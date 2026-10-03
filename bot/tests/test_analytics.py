import datetime
import os
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.database.database import async_session
from bot.database.models import WeatherData
from bot.services.analytics import WeatherAnalytics


async def test_weekly_analysis(make_user):
    """Тенденции за неделю: теплеет, влажность падает, ветер слабеет."""
    user_id = await make_user(user_id=999999, city="TestCity")

    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    async with async_session() as session:
        for i in range(7):
            # i=6 самая старая запись, i=0 самая свежая
            session.add(
                WeatherData(
                    user_id=user_id,
                    temperature=20.0 - i,
                    feels_like=19.0 - i,
                    pressure=1010 + i,
                    humidity=60 + i,
                    wind_speed=5.0 + i * 0.5,
                    description="Облачно",
                    date=now - datetime.timedelta(days=i),
                )
            )
        await session.commit()

    # get_weekly_analysis ждёт внутренний User.id, а не Telegram-ID
    analysis = await WeatherAnalytics.get_weekly_analysis(user_id)

    assert analysis is not None
    assert analysis["city"] == "TestCity"
    trends = analysis["trends"]
    assert trends["temperature"]["description"] == "повышение"
    assert trends["humidity"]["description"] == "понижение"
    assert trends["wind"]["description"] == "ослабление"


async def test_weekly_analysis_unknown_user(db):
    """Несуществующий пользователь: None, без исключения."""
    assert await WeatherAnalytics.get_weekly_analysis(424242) is None


@pytest.fixture
def tz_los_angeles():
    """Пояс процесса UTC-7/-8: datetime.now() отстаёт от UTC (только Unix)."""
    old = os.environ.get("TZ")
    os.environ["TZ"] = "America/Los_Angeles"
    time.tzset()
    yield
    if old is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = old
    time.tzset()


async def test_weekly_analysis_window_is_utc(make_user, tz_los_angeles):
    """Записи, сохранённые БД (UTC), попадают в окно при любом поясе процесса."""
    user_id = await make_user(user_id=555, city="TestCity")
    weather = {
        "temperature": 10.0,
        "feels_like": 9.0,
        "pressure": 1010,
        "humidity": 70,
        "wind_speed": 3.0,
        "description": "Облачно",
    }
    for _ in range(2):
        await WeatherAnalytics.save_weather_data_for_week_analysis(user_id, weather)

    analysis = await WeatherAnalytics.get_weekly_analysis(user_id)

    assert analysis is not None


async def test_weekly_analysis_groups_by_city_local_date(make_user):
    """00:30 и 23:00 по местному времени это один день, хотя в UTC их два."""
    user_id = await make_user(user_id=777, city="Москва", timezone_offset=10800)

    today = datetime.datetime.now(datetime.UTC).replace(
        tzinfo=None, hour=0, minute=0, second=0, microsecond=0
    )
    base = today - datetime.timedelta(days=3)  # 00:00 UTC, три дня назад
    # 21:30 UTC накануне = 00:30 в Москве, 20:00 UTC = 23:00 в Москве
    moments = [
        base - datetime.timedelta(hours=2, minutes=30),
        base + datetime.timedelta(hours=20),
    ]
    async with async_session() as session:
        for moment in moments:
            session.add(
                WeatherData(
                    user_id=user_id,
                    temperature=10.0,
                    feels_like=9.0,
                    pressure=1010,
                    humidity=70,
                    wind_speed=3.0,
                    description="Облачно",
                    date=moment,
                )
            )
        await session.commit()

    analysis = await WeatherAnalytics.get_weekly_analysis(user_id)

    assert analysis is not None
    assert len(analysis["daily_analysis"]) == 1
    assert analysis["period"]["start"] == base.date()


async def test_weekly_analysis_with_forecast(make_user):
    """Воскресная рассылка: анализ прошлой недели из БД + прогноз из API."""
    user_id = await make_user(user_id=888, city="Москва")
    weather = {
        "temperature": 10.0,
        "feels_like": 9.0,
        "pressure": 1010,
        "humidity": 70,
        "wind_speed": 3.0,
        "description": "Облачно",
    }
    for _ in range(2):
        await WeatherAnalytics.save_weather_data_for_week_analysis(user_id, weather)

    forecast = {
        "city": "Москва",
        "country": "RU",
        "forecasts": [
            {
                "date": datetime.date(2026, 10, 3),
                "avg_temp": 5.0,
                "min_temp": 2.0,
                "max_temp": 8.0,
                "avg_humidity": 80.0,
                "avg_wind": 4.0,
                "description": "дождь",
            }
        ],
    }
    weather_api = MagicMock()
    weather_api.get_forecast = AsyncMock(return_value=forecast)

    result = await WeatherAnalytics.get_weekly_analysis_with_forecast(
        user_id, weather_api
    )

    assert result is not None
    assert result["city"] == "Москва"
    assert result["past_week"] is not None
    assert result["next_week_forecast"]["days_count"] == 1
    weather_api.get_forecast.assert_awaited_once_with("Москва", days=5)

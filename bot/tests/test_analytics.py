import datetime
import os
import time

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

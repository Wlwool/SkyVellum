import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import func, select

from bot.database.database import async_session
from bot.database.models import User, WeatherData
from bot.handlers import weather
from bot.services.weather_api import CityNotFoundError, WeatherServiceError

TELEGRAM_ID = 123456
API_ERRORS = [
    (WeatherServiceError("сбой"), "недоступен"),
    (CityNotFoundError("нет такого"), "Изменить город"),
]


def _message() -> MagicMock:
    """Подделка сообщения Telegram: автор, время и метод answer."""
    message = MagicMock()
    message.from_user = SimpleNamespace(id=TELEGRAM_ID)
    message.date = datetime.datetime(2026, 10, 2, 10, 0, tzinfo=datetime.UTC)
    message.answer = AsyncMock()
    return message


def _weather(tz_offset: int) -> dict:
    """Ответ get_current_weather с теми же ключами, что у настоящего API."""
    return {
        "city": "Новосибирск",
        "country": "RU",
        "temperature": 10.0,
        "feels_like": 8.0,
        "pressure": 1010,
        "humidity": 70,
        "wind_speed": 3.0,
        "description": "ясно",
        "sunrise": 1_790_900_000,
        "sunset": 1_790_940_000,
        "timezone": tz_offset,
    }


async def test_weather_now_updates_timezone_offset(make_user):
    """'Погода сейчас' подтягивает смещение пояса из ответа OpenWeather."""
    await make_user(user_id=TELEGRAM_ID)

    with patch.object(
        weather.weather_api,
        "get_current_weather",
        new=AsyncMock(return_value=_weather(25200)),
    ):
        await weather.get_weather_now(_message())

    async with async_session() as session:
        result = await session.execute(
            select(User.timezone_offset).where(User.user_id == TELEGRAM_ID)
        )
        assert result.scalar_one() == 25200


async def test_weather_now_does_not_save_weather_data(make_user):
    """'Погода сейчас' не пишет в WeatherData: анализ идёт по утренней рассылке."""
    await make_user(user_id=TELEGRAM_ID)

    with patch.object(
        weather.weather_api,
        "get_current_weather",
        new=AsyncMock(return_value=_weather(10800)),
    ):
        await weather.get_weather_now(_message())

    async with async_session() as session:
        result = await session.execute(select(func.count()).select_from(WeatherData))
        assert result.scalar_one() == 0


def _answered_text(message: MagicMock) -> str:
    message.answer.assert_awaited_once()
    return str(message.answer.call_args.args[0])


@pytest.mark.parametrize(("error", "expected"), API_ERRORS)
async def test_weather_now_api_errors(make_user, error, expected):
    """Сбой OpenWeather: человек получает понятный ответ, а не падение."""
    await make_user(user_id=TELEGRAM_ID)
    message = _message()

    with patch.object(
        weather.weather_api, "get_current_weather", new=AsyncMock(side_effect=error)
    ):
        await weather.get_weather_now(message)

    assert expected in _answered_text(message)


@pytest.mark.parametrize(("error", "expected"), API_ERRORS)
async def test_forecast_api_errors(make_user, error, expected):
    """То же для прогноза на 5 дней."""
    await make_user(user_id=TELEGRAM_ID)
    message = _message()

    with patch.object(
        weather.weather_api, "get_forecast", new=AsyncMock(side_effect=error)
    ):
        await weather.get_weather_forecast(message)

    assert expected in _answered_text(message)


async def test_weather_now_without_sunrise_and_sunset(make_user):
    """Нет восхода и заката (полярный день или ночь)"""
    await make_user(user_id=TELEGRAM_ID)
    message = _message()
    data = {**_weather(10800), "sunrise": None, "sunset": None}

    with patch.object(
        weather.weather_api, "get_current_weather", new=AsyncMock(return_value=data)
    ):
        await weather.get_weather_now(message)

    text = _answered_text(message)
    assert "Восход солнца: нет данных" in text
    assert "Закат солнца: нет данных" in text


def _forecast_data() -> dict:
    """Ответ get_forecast: два дня с теми же ключами, что у настоящего API."""
    return {
        "city": "Новосибирск",
        "country": "RU",
        "forecasts": [
            {
                "date": datetime.date(2026, 10, 3),
                "avg_temp": 5.0,
                "min_temp": 1.0,
                "max_temp": 9.0,
                "avg_humidity": 70.0,
                "avg_wind": 3.0,
                "description": "ясно",
            },
            {
                "date": datetime.date(2026, 10, 4),
                "avg_temp": 6.0,
                "min_temp": 2.0,
                "max_temp": 10.0,
                "avg_humidity": 65.0,
                "avg_wind": 4.0,
                "description": "облачно",
            },
        ],
    }


async def test_weather_now_success_text(make_user):
    """Страховка: полный текст «Погоды сейчас» до и после выноса форматирования."""
    await make_user(user_id=TELEGRAM_ID)
    message = _message()

    with patch.object(
        weather.weather_api,
        "get_current_weather",
        new=AsyncMock(return_value=_weather(10800)),
    ):
        await weather.get_weather_now(message)

    text = _answered_text(message)
    assert "Погода в городе Новосибирск (RU):" in text
    assert "Температура: 10.0°C (ощущается как 8.0°C)" in text
    assert "Данные обновлены: 13:00:00" in text


async def test_forecast_success_text(make_user):
    """Страховка: текст прогноза на 5 дней до и после выноса форматирования."""
    await make_user(user_id=TELEGRAM_ID)
    message = _message()

    with patch.object(
        weather.weather_api,
        "get_forecast",
        new=AsyncMock(return_value=_forecast_data()),
    ):
        await weather.get_weather_forecast(message)

    text = _answered_text(message)
    assert "Прогноз погоды на 5 дней для города Новосибирск (RU):" in text
    assert "📅 03.10:" in text
    assert "Температура: 5.0°C (от 1.0°C до 9.0°C)" in text
    assert "📅 04.10:" in text

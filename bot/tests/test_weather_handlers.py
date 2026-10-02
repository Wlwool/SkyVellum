import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select

from bot.database.database import async_session
from bot.database.models import User
from bot.handlers import weather

TELEGRAM_ID = 123456


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

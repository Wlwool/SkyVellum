from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.future import select

from bot.database.database import async_session
from bot.database.models import User
from bot.handlers.registration import process_city

TELEGRAM_ID = 123456


def _message(text: str) -> MagicMock:
    """Подделка сообщения Telegram: нужны текст, автор и метод answer."""
    message = MagicMock()
    message.text = text
    message.from_user = SimpleNamespace(
        id=TELEGRAM_ID, username="ivan", first_name="Иван", last_name=None
    )
    message.answer = AsyncMock()
    return message


async def _register(city: str, tz_offset: int) -> None:
    """Прогоняет process_city, подменив ответ OpenWeather."""
    api = MagicMock()
    api.get_current_weather = AsyncMock(
        return_value={"lat": 55.0, "lon": 83.0, "timezone": tz_offset}
    )
    with patch("bot.handlers.registration.WeatherAPI", return_value=api):
        await process_city(_message(city), AsyncMock())


async def _get_user() -> User:
    async with async_session() as session:
        stmt = select(User).where(User.user_id == TELEGRAM_ID)
        result = await session.execute(stmt)
        return result.scalar_one()


async def test_new_user_gets_city_timezone(db):
    """Новый пользователь сохраняется со смещением своего города."""
    await _register("Новосибирск", tz_offset=25200)
    user = await _get_user()
    assert user.timezone_offset == 25200


async def test_city_change_updates_timezone(make_user):
    """При смене города смещение обновляется вместе с городом."""
    await make_user(user_id=TELEGRAM_ID, city="Москва")
    await _register("Новосибирск", tz_offset=25200)

    user = await _get_user()
    assert user.city == "Новосибирск"
    assert user.timezone_offset == 25200

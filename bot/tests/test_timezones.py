from unittest.mock import AsyncMock

from sqlalchemy import select

from bot.database.database import async_session
from bot.database.models import User
from bot.services.timezones import refresh_timezone_offsets
from bot.services.weather_api import CityNotFoundError

OFFSETS = {"Москва": 10800, "Омск": 21600}


async def _lookup(city: str) -> dict[str, int]:
    """Подделка get_current_weather: знает только города из OFFSETS."""
    offset = OFFSETS.get(city)
    if offset is None:
        raise CityNotFoundError(city)
    return {"timezone": offset}


def _api() -> AsyncMock:
    api = AsyncMock()
    api.get_current_weather.side_effect = _lookup
    return api


async def _offset(user_id: int) -> int:
    async with async_session() as session:
        result = await session.execute(
            select(User.timezone_offset).where(User.user_id == user_id)
        )
        return int(result.scalar_one())


async def test_refresh_sets_offsets_from_api(make_user):
    """Смещения активных пользователей берутся из ответа OpenWeather."""
    await make_user(user_id=111, city="Москва")
    await make_user(user_id=222, city="Омск")

    result = await refresh_timezone_offsets(_api())

    assert result == (2, 0)
    assert await _offset(111) == 10800
    assert await _offset(222) == 21600


async def test_refresh_counts_failed_lookup(make_user):
    """Если API ничего не вернул, смещение остаётся прежним, сбой считается."""
    await make_user(user_id=111, city="Москва")
    await make_user(user_id=222, city="Несуществующий")

    result = await refresh_timezone_offsets(_api())

    assert result == (1, 1)
    assert await _offset(111) == 10800
    assert await _offset(222) == 0


async def test_refresh_skips_inactive_users(make_user):
    """Неактивным запросы к API не уходят."""
    await make_user(user_id=111, city="Москва", is_active=False)
    api = _api()

    result = await refresh_timezone_offsets(api)

    assert result == (0, 0)
    api.get_current_weather.assert_not_awaited()
    assert await _offset(111) == 0

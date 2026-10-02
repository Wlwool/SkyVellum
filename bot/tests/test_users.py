from sqlalchemy import select

from bot.database.database import async_session
from bot.database.models import User
from bot.services.users import update_timezone_offset


async def _offset(user_pk: int) -> int:
    async with async_session() as session:
        result = await session.execute(
            select(User.timezone_offset).where(User.id == user_pk)
        )
        return int(result.scalar_one())


async def test_update_timezone_offset(make_user):
    """Смещение пользователя заменяется новым значением."""
    user_pk = await make_user()

    await update_timezone_offset(user_pk, 10800)
    assert await _offset(user_pk) == 10800


async def test_update_timezone_offset_overwrites(make_user):
    """Повторный вызов перезаписывает значение (например, перевод часов)."""
    user_pk = await make_user()
    await update_timezone_offset(user_pk, 10800)

    await update_timezone_offset(user_pk, 7200)

    assert await _offset(user_pk) == 7200


async def test_update_timezone_offset_only_target_user(make_user):
    """Остальные пользователи не затрагиваются."""
    first = await make_user(user_id=111)
    second = await make_user(user_id=222)

    await update_timezone_offset(first, 10800)
    assert await _offset(first) == 10800
    assert await _offset(second) == 0

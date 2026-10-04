from sqlalchemy import func, select

from bot.database.database import async_session
from bot.database.models import User
from bot.services.users import (
    get_user_by_telegram_id,
    save_user,
    set_user_active,
    update_timezone_offset,
)


async def _offset(user_pk: int) -> int:
    async with async_session() as session:
        result = await session.execute(
            select(User.timezone_offset).where(User.id == user_pk)
        )
        return int(result.scalar_one())


async def _is_active(user_pk: int) -> bool | None:
    async with async_session() as session:
        result = await session.execute(select(User.is_active).where(User.id == user_pk))
        return result.scalar_one()


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


async def test_get_user_by_telegram_id_found(make_user):
    """Пользователь находится по Telegram ID."""
    await make_user(user_id=111, city="Тамбов")

    user = await get_user_by_telegram_id(111)

    assert user is not None
    assert user.city == "Тамбов"


async def test_get_user_by_telegram_id_not_found(make_user):
    """Нет такого Telegram ID: возвращается None, а не исключение."""
    await make_user(user_id=111)

    assert await get_user_by_telegram_id(999) is None


async def test_get_user_by_telegram_id_ignores_internal_id(make_user):
    """Ищем по Telegram ID, а не по внутреннему User.id (частая путаница)."""
    user_pk = await make_user(user_id=111)

    assert await get_user_by_telegram_id(user_pk) is None


async def test_set_user_active_deactivates(make_user):
    """Бот заблокирован: пользователь становится неактивным."""
    user_pk = await make_user()

    await set_user_active(user_pk, False)

    assert await _is_active(user_pk) is False


async def test_set_user_active_reactivates(make_user):
    """Пользователь вернулся по /start: снова активен."""
    user_pk = await make_user(is_active=False)

    await set_user_active(user_pk, True)

    assert await _is_active(user_pk) is True


async def test_set_user_active_only_target_user(make_user):
    """Остальные пользователи не затрагиваются."""
    first = await make_user(user_id=111)
    second = await make_user(user_id=222)

    await set_user_active(first, False)

    assert await _is_active(first) is False
    assert await _is_active(second) is True


async def _save(telegram_id: int, city: str = "Тамбов") -> bool:
    return await save_user(
        telegram_id,
        username="vasya",
        first_name="Вася",
        last_name=None,
        city=city,
        latitude=52.7,
        longitude=41.4,
        timezone_offset=10800,
    )


async def test_save_user_creates_new(db):
    """Нового пользователя создаём со всеми полями; True = создан."""
    assert await _save(111) is True

    user = await get_user_by_telegram_id(111)
    assert user is not None
    assert user.city == "Тамбов"
    assert user.username == "vasya"
    assert user.latitude == 52.7
    assert user.timezone_offset == 10800
    assert user.is_active is True


async def test_save_user_updates_existing(make_user):
    """Существующему меняем город, координаты и пояс; False = обновлён."""
    await make_user(user_id=111, city="Москва")

    assert await _save(111, city="Тамбов") is False

    user = await get_user_by_telegram_id(111)
    assert user is not None
    assert user.city == "Тамбов"
    assert user.latitude == 52.7
    assert user.longitude == 41.4
    assert user.timezone_offset == 10800


async def test_save_user_does_not_duplicate(make_user):
    """Повторная регистрация не создаёт вторую строку."""
    await make_user(user_id=111)

    await _save(111)

    async with async_session() as session:
        result = await session.execute(select(func.count()).select_from(User))
        assert result.scalar_one() == 1

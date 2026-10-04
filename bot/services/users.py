from sqlalchemy import select, update

from bot.database.database import async_session
from bot.database.models import User


async def get_active_users() -> list[User]:
    """Все активные пользователи (is_active = True)"""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.is_active.is_(True)))
        return list(result.scalars().all())


async def update_timezone_offset(user_pk: int, offset: int) -> None:
    """Обновляет смещение часового пояса пользователя, если оно изменилось.
    user_pk - внутренний User.id.
    offset - секунды от UTC из ответа OpenWeather.
    Условие `timezone_offset != offset` не даёт делать лишнюю запись в БД,
    пока смещение то же самое.
    """
    async with async_session() as session:
        await session.execute(
            update(User)
            .where(User.id == user_pk, User.timezone_offset != offset)
            .values(timezone_offset=offset)
        )
        await session.commit()


async def get_user_by_telegram_id(telegram_id: int) -> User | None:
    """Пользователь по Telegram ID (User.user_id) или None, если не найден.
    Внутренний ключ User.id здесь не подходит: для него другой запрос.
    """
    async with async_session() as session:
        result = await session.execute(select(User).where(User.user_id == telegram_id))
        return result.scalar_one_or_none()

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


async def set_user_active(user_pk: int, is_active: bool) -> None:
    """Включает или выключает пользователя. user_pk - внутренний User.id.
    False: бот заблокирован, рассылки пропускаются.
    True: человек вернулся по /start.
    """
    async with async_session() as session:
        await session.execute(
            update(User).where(User.id == user_pk).values(is_active=is_active)
        )
        await session.commit()


async def save_user(
    telegram_id: int,
    *,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
    city: str,
    latitude: float,
    longitude: float,
    timezone_offset: int,
) -> bool:
    """Регистрирует пользователя или обновляет ему город.
    Новому пользователю записываются все поля. У существующего меняются только
    город, координаты и пояс, имя и username остаются прежними.
    Возвращает True, если пользователь создан, и False, если обновлён.
    """
    async with async_session() as session:
        result = await session.execute(select(User).where(User.user_id == telegram_id))
        user = result.scalar_one_or_none()

        if user:
            user.city = city
            user.latitude = latitude
            user.longitude = longitude
            user.timezone_offset = timezone_offset
            await session.commit()
            return False

        session.add(
            User(
                user_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                city=city,
                latitude=latitude,
                longitude=longitude,
                timezone_offset=timezone_offset,
            )
        )
        await session.commit()
        return True

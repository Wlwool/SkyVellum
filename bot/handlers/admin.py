import logging
from aiogram import Dispatcher, types
from aiogram.filters import Command
from sqlalchemy import func
from sqlalchemy.future import select
from bot.config.config import Config
from bot.database.models import User
from bot.database.database import async_session


logger = logging.getLogger(__name__)
config = Config()


async def cmd_stats(message: types.Message):
    """Команда /stats для получения статистики бота для админа
    Предоставляет статистику использования бота:
    - Общее количество пользователей
    - Количество активных пользователей
    - Топ городов по количеству пользователей

    Аргументы:
        message: types.Message - Объект сообщения от пользователя

    Доступ:
        Только для пользователей, указанных в config.ADMIN_IDS

    Действия:
        1. Проверяет права администратора
        2. Формирует статистические данные из БД
        3. Отправляет сводку администратору
    """
    user_id = message.from_user.id

    # проверяем, является ли пользователь админом
    if user_id not in config.ADMIN_IDS:
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    # получение статистики пользователей
    async with async_session() as session:
        # общее количество пользователей
        total_users_result = await session.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar_one()

        # количество активных пользователей
        active_users_result = await session.execute(select(func.count(User.id)).where(User.is_active.is_(True)))
        active_users = active_users_result.scalar_one()

        # города пользователей
        cities_result = await session.execute(
            select(User.city, func.count(User.id))
            .group_by(User.city)
            .order_by(func.count(User.id).desc())
        )
        cities = cities_result.all()

    # формируем сообщение со статистикой
    stats_message = (
        f"📊 Статистика бота:\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"✅ Активных пользователей: {active_users}\n\n"
        f"🏙️ Топ городов:\n"
    )

    for city, count in cities[:10]:
        stats_message += f"- {city}: {count} пользователей\n"

    await message.answer(stats_message)


def register_admin_handlers(dp: Dispatcher):
    """Регистрация обработчиков команд администратора"""
    dp.message.register(cmd_stats, Command("stats"))

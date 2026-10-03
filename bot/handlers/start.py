import logging

from aiogram import Dispatcher, types
from aiogram.filters import Command
from sqlalchemy.future import select

from bot.database.database import async_session
from bot.database.models import User
from bot.keyboards.reply import get_start_keyboard

logger = logging.getLogger(__name__)


async def cmd_start(message: types.Message) -> None:
    """Команда /start для запуска бота."""
    if message.from_user is None:
        return
    user_id = message.from_user.id

    # Проверка регистрации пользователя
    async with async_session() as session:
        stmt = select(User).where(User.user_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            if user:
                if not user.is_active:
                    user.is_active = True
                    await session.commit()
            await message.answer(
                f"Привет, {message.from_user.first_name}!\n"
                f"Вы уже зарегистрированы!\nВаш город: {user.city.capitalize()}.",
                reply_markup=get_start_keyboard(is_registered=True),
            )
        else:
            await message.answer(
                f"Привет, {message.from_user.first_name}!\n"
                f"Добро пожаловать в бота прогноза погоды. ☀️\n"
                f"Для получения информации о погоде, вам необходимо "
                f"зарегистрироваться и указать свой город.",
                reply_markup=get_start_keyboard(is_registered=False),
            )


def register_start_handlers(dp: Dispatcher) -> None:
    """Регистрация обработчиков команды /start"""
    dp.message.register(cmd_start, Command("start"))

import logging
from aiogram import Dispatcher, types
from aiogram.filters import Command
from sqlalchemy.future import select
from bot.database.models import User
from bot.database.database import async_session
from bot.keyboards.reply import get_start_keyboard


logger = logging.getLogger(__name__)


async def cmd_start(message: types.Message) -> None:
    """Команда /start для запуска бота."""
    user_id = message.from_user.id

    # Проверка регистрации пользователя
    async with async_session() as session:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            await message.answer(
                f"Привет, {message.from_user.first_name}!"
                f"Вы уже зарегистрированы! Ваш город: {user.city}.",
                reply_markup=get_start_keyboard(is_registered=True)
            )
        else:
            await message.answer(
                f"Привет, {message.from_user.first_name}!"
                f"Добро пожаловать в бота прогноза погоды. "
                f"Для получения информации о погоде, вам необходимо зарегистрироваться и указать свой город.",
                reply_markup=get_start_keyboard(is_registered=False)
            )

def register_start_handlers(dp: Dispatcher) -> None:
    """Регистрация обработчиков команды /start"""
    dp.message.register(cmd_start, Command("start"))

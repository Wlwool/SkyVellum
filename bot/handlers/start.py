import logging

from aiogram import Dispatcher, types
from aiogram.filters import Command

from bot.keyboards.reply import get_start_keyboard
from bot.services.users import get_user_by_telegram_id, set_user_active

logger = logging.getLogger(__name__)


async def cmd_start(message: types.Message) -> None:
    """Команда /start для запуска бота."""
    if message.from_user is None:
        return

    # Проверка регистрации пользователя
    user = await get_user_by_telegram_id(message.from_user.id)

    if user:
        # вернулся тот, кто заблокировал бота: снова включаем рассылки
        if not user.is_active:
            await set_user_active(user.id, True)
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

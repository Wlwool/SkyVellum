import logging
from typing import Any

from aiogram import Dispatcher, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.handlers.texts import SERVICE_UNAVAILABLE
from bot.keyboards.reply import get_start_keyboard
from bot.services.users import save_user
from bot.services.weather_api import CityNotFoundError, WeatherServiceError, weather_api

logger = logging.getLogger(__name__)


class RegistrationForm(StatesGroup):
    """Состояния FSM для регистрации пользователя."""

    waiting_for_city = State()


async def register_command(message: types.Message, state: FSMContext) -> None:
    """Функция обработки команды регистрации пользователя."""
    await message.answer(
        "Для регистрации укажите свой город, "
        "чтобы я мог присылать вам информацию о погоде.",
        reply_markup=types.ReplyKeyboardRemove(),
    )

    await state.set_state(RegistrationForm.waiting_for_city)


async def process_city(message: types.Message, state: FSMContext) -> None:
    """Функция обработки введенного города пользователем."""
    if message.from_user is None:
        return
    if message.text is None:
        await message.answer("Пожалуйста, отправьте название города текстом.")
        return
    city = message.text.strip()

    # Проверка на наличие города через API погоды
    try:
        weather_data: dict[str, Any] = await weather_api.get_current_weather(city)
    except CityNotFoundError:
        await message.answer(
            "Извините, но не удалось найти введенный вами город. "
            "Пожалуйста, проверьте правильность написания и попробуйте еще раз. "
            "Примеры: Москва, Тамбов, Санкт-Петербург и т.д."
        )
        return
    except WeatherServiceError:
        await message.answer(SERVICE_UNAVAILABLE)
        return

    # Сохранение пользователя: новый создаётся, существующему меняется город
    user_id = message.from_user.id
    is_new = await save_user(
        user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        city=city,
        latitude=weather_data["lat"],
        longitude=weather_data["lon"],
        timezone_offset=weather_data["timezone"],
    )

    if is_new:
        logger.info(f"Зарегистрирован новый пользователь ({user_id}), город: {city}")
        await message.answer(
            f"Вы успешно зарегистрированы! "
            f"Теперь вы будете получать информацию о погоде для города {city}.",
            reply_markup=get_start_keyboard(is_registered=True),
        )
    else:
        logger.info(f"Обновление данных пользователя ({user_id}), город: {city}")
        await message.answer(
            f"Ваш город успешно обновлен. "
            f"Теперь вы будете получать информацию о погоде для города {city}.",
            reply_markup=get_start_keyboard(is_registered=True),
        )
    # Очистка состояния FSM после успешной регистрации
    await state.clear()


def register_registration_handlers(dp: Dispatcher):
    """Функция регистрации обработчиков для регистрации пользователя."""
    dp.message.register(register_command, F.text == "Зарегистрироваться")
    dp.message.register(process_city, RegistrationForm.waiting_for_city)

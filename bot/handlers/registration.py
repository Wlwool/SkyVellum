import logging
from aiogram import Dispatcher, types
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.future import select
from bot.database.models import User
from bot.database.database import async_session
from bot.keyboards.reply import get_start_keyboard
from bot.services.weather_api import WeatherAPI

logger = logging.getLogger(__name__)


class RegistrationForm(StatesGroup):
    """Состояния FSM для регистрации пользователя."""
    waiting_for_city = State()

async def register_command(message: types.Message, state: FSMContext):
    """Функция обработки команды регистрации пользователя."""
    await message.answer("Для регистрации укажите свой город, чтобы я мог присылать вам информацию о погоде.",
                         reply_markup=types.ReplyKeyboardRemove())

    await state.set_state(RegistrationForm.waiting_for_city)

async def process_city(message: types.Message, state: FSMContext):
    """Функция обработки введенного города пользователем."""
    city = message.text.strip().lower()

    # Проверка на наличие города через API погоды
    weather_api = WeatherAPI()
    weather_data = await weather_api.get_weather(city)

    if not weather_data:
        await message.answer("Извините, но не удалось найти введенный вами город. "
                             "Пожалуйста, проверьте правильность написания и попробуйте еще раз. "
                             "Примеры: Москва, Тамбов, Санкт-Петербург и т.д.")
        return

    # Получение информации о пользователе
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    async with async_session() as session:
        # Проверка, зарегистрирован ли пользователь
        stmt = select(User).where(User.user_id == user_id)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            # Если пользователь уже зарегистрирован, обновляем данные
            existing_user.city = city
            existing_user.latitude = weather_data["lat"]
            existing_user.longitude = weather_data["lon"]
            await session.commit()
            logger.info(f"Обновление данных пользователя ({user_id}), город: {city}")
            await message.answer(
                f"Ваш город успешно обновлен. Теперь вы будете получать информацию о погоде для города {city}.",
                reply_markup=get_start_keyboard(is_registered=True)
            )
        else:
            # Если пользователь не зарегистрирован, создаем нового пользователя
            new_user = User(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                city=city,
                latitude=weather_data["lat"],
                longitude=weather_data["lon"]
                )
            session.add(new_user)
            await session.commit()
            logger.info(f"Зарегистрирован новый пользователь ({user_id}), город: {city}")
            await message.answer(
                f"Вы успешно зарегистрированы! Теперь вы будете получать информацию о погоде для города {city}.",
                reply_markup=get_start_keyboard(is_registered=True)
            )
    # Очистка состояния FSM после успешной регистрации
    await state.clear()

def register_registration_handlers(dp: Dispatcher):
    """Функция регистрации обработчиков для регистрации пользователя."""
    dp.message.register(register_command, Text(text="Регистрация"))   # (startswith="👋", ignore_case=True)
    dp.message.register(process_city, RegistrationForm.waiting_for_city)


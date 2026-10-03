import logging
from typing import Any

from aiogram import Dispatcher, F, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select

from bot.database.database import async_session
from bot.database.models import User
from bot.handlers.texts import CITY_NOT_FOUND_SAVED, SERVICE_UNAVAILABLE
from bot.keyboards.reply import get_start_keyboard, get_weather_keyboard
from bot.services.analytics import WeatherAnalytics
from bot.services.users import update_timezone_offset
from bot.services.weather_api import CityNotFoundError, WeatherAPI, WeatherAPIError
from bot.utils.timeutils import format_local_time

logger = logging.getLogger(__name__)
weather_api = WeatherAPI()


def _api_error_text(error: WeatherAPIError) -> str:
    """Что ответить человеку, если OpenWeather не дал данных."""
    if isinstance(error, CityNotFoundError):
        return CITY_NOT_FOUND_SAVED
    return SERVICE_UNAVAILABLE


def _local_time_or_no_data(timestamp: int | None, tz_offset: int) -> str:
    """Местное время для вывода. Нет значения (полярный день/ночь) - нет данных"""
    if timestamp is None:
        return "нет данных"
    return format_local_time(timestamp, tz_offset)


async def get_weather_now(message: types.Message):
    """Получение текущей информации о погоде"""
    if message.from_user is None:
        return
    user_id = message.from_user.id

    # получение данных о пользователе
    async with async_session() as session:
        stmt = select(User).where(User.user_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

    if not user:
        await message.answer(
            "Вы еще не зарегистрированы. "
            "Пожалуйста, зарегистрируйтесь, чтобы получать прогноз погоды",
            reply_markup=get_start_keyboard(is_registered=False),
        )
        return

    # получение данных о погоде для города, который был выбран пользователем
    try:
        weather_data: dict[str, Any] = await weather_api.get_current_weather(user.city)
    except WeatherAPIError as e:
        await message.answer(_api_error_text(e), reply_markup=get_weather_keyboard())
        return

    await update_timezone_offset(
        user.id,
        weather_data["timezone"],
    )

    # Преобразование времени заката и рассвета в читаемый формат
    tz_offset = weather_data["timezone"]
    sunrise_time = _local_time_or_no_data(weather_data["sunrise"], tz_offset)
    sunset_time = _local_time_or_no_data(weather_data["sunset"], tz_offset)
    formatted_time = format_local_time(int(message.date.timestamp()), tz_offset)

    # ответное сообщение с текущей погодой пользователю
    weather_message = (
        f"Погода в городе {weather_data['city']} ({weather_data['country']}):\n\n"
        f"🌡️ Температура: {weather_data['temperature']:.1f}°C "
        f"(ощущается как {weather_data['feels_like']:.1f}°C)\n"
        f"💧 Влажность: {weather_data['humidity']}%\n"
        f"🌬️ Ветер: {weather_data['wind_speed']} м/с\n"
        f"🔍 {weather_data['description'].capitalize()}\n\n"
        f"🌅 Восход солнца: {sunrise_time}\n"
        f"🌇 Закат солнца: {sunset_time}\n\n"
        f"🕒 Данные обновлены: {formatted_time}\n*** Хорошего дня! ***"
    )
    await message.answer(weather_message, reply_markup=get_weather_keyboard())


async def get_weather_forecast(message: types.Message) -> None:
    """Получение прогноза погоды на 5 дней"""
    if message.from_user is None:
        return
    try:
        user_id = message.from_user.id

        # получение данных о пользователе
        async with async_session() as session:
            stmt = select(User).where(User.user_id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

        if not user:
            await message.answer(
                "Вы еще не зарегистрированы. "
                "Пожалуйста, зарегистрируйтесь, чтобы получать прогноз погоды",
                reply_markup=get_start_keyboard(is_registered=False),
            )
            return
        # получение прогноза погоды для города, который был выбран пользователем
        forecast_data = await weather_api.get_forecast(user.city, days=5)
        logger.debug(f"Прогноз получен для города {user.city}")

        # ответное сообщение с прогнозом погоды пользователю
        forecast_message = (
            f"Прогноз погоды на 5 дней для города "
            f"{forecast_data['city']} "
            f"({forecast_data['country']}):\n\n"
        )

        for forecast in forecast_data["forecasts"][:5]:  # Берем только первые 5 дней
            date_str = forecast["date"].strftime("%d.%m")
            forecast_message += (
                f"📅 {date_str}:\n"
                f"🌡️ Температура: {forecast['avg_temp']:.1f}°C "
                f"(от {forecast['min_temp']:.1f}°C до {forecast['max_temp']:.1f}°C)\n"
                f"💧 Влажность: {forecast['avg_humidity']:.0f}%\n"
                f"🌬️ Ветер: {forecast['avg_wind']:.1f} м/с\n"
                f"🔍 {forecast['description'].capitalize()}\n\n"
            )
        await message.answer(forecast_message, reply_markup=get_weather_keyboard())
    except WeatherAPIError as e:
        await message.answer(_api_error_text(e), reply_markup=get_weather_keyboard())
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer("Произошла внутренняя ошибка при получении прогноза.")


async def get_weekly_analysis(message: types.Message) -> None:
    """Получение недельного анализа погоды"""
    if message.from_user is None:
        return
    user_id = message.from_user.id

    # Получение данных о пользователе
    async with async_session() as session:
        stmt = select(User).where(User.user_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

    if not user:
        await message.answer(
            "Вы еще не зарегистрированы. "
            "Пожалуйста, зарегистрируйтесь, чтобы получать прогноз погоды",
            reply_markup=get_start_keyboard(is_registered=False),
        )
        return

    # Получение еженедельного анализа погоды
    analysis_data = await WeatherAnalytics().get_weekly_analysis(user.id)

    if not analysis_data:
        await message.answer(
            "Извините, не удалось получить анализ погоды. "
            "Возможно, недостаточно данных для анализа. "
            "Попробуй позже, когда будет собрано больше данных.",
            reply_markup=get_weather_keyboard(),
        )
        return

    # формирование сообщения с еженедельным анализом погоды
    start_date = analysis_data["period"]["start"].strftime("%d.%m")
    end_date = analysis_data["period"]["end"].strftime("%d.%m")

    analysis_message = (
        f"Анализ погоды за период {start_date} - {end_date} "
        f"для города {analysis_data['city']}:\n\n"
    )

    # информация о тенденциях температуры, влажности и ветра
    if analysis_data["trends"]:
        analysis_message += "📊 Тенденции за неделю:\n"
        analysis_message += (
            f"🌡️ Температура: {analysis_data['trends']['temperature']['description']} "
        )
        analysis_message += (
            f"({analysis_data['trends']['temperature']['value']:.1f}°C)\n"
        )
        analysis_message += (
            f"💧 Влажность: {analysis_data['trends']['humidity']['description']} "
        )
        analysis_message += f"({analysis_data['trends']['humidity']['value']:.1f}%)\n"
        analysis_message += (
            f"🌬️ Ветер: {analysis_data['trends']['wind']['description']} "
        )
        analysis_message += f"({analysis_data['trends']['wind']['value']:.1f} м/с)\n\n"

    # информация по дням за неделю
    analysis_message += "📅 Данные по дням:\n"
    for day_data in analysis_data["daily_analysis"]:
        date_str = day_data["date"].strftime("%d.%m")
        analysis_message += (
            f"- {date_str}: {day_data['avg_temp']:.1f}°C, "
            f"влажность {day_data['avg_humidity']:.0f}%, "
            f"ветер {day_data['avg_wind']:.1f} м/с\n"
        )
    await message.answer(analysis_message, reply_markup=get_weather_keyboard())


async def change_city(message: types.Message, state: FSMContext):
    """Смена города"""
    from bot.handlers.registration import register_command

    await register_command(message, state)


def register_weather_handlers(dp: Dispatcher):
    """Регистрация обработчиков команд для погоды"""
    dp.message.register(get_weather_now, F.text == "Погода сейчас")
    dp.message.register(get_weather_forecast, F.text == "Погода на 5 дней")
    dp.message.register(get_weekly_analysis, F.text == "Еженедельный анализ")
    dp.message.register(change_city, F.text == "Изменить город")

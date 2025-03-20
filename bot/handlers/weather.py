import logging
from aiogram import Dispatcher, types
from aiogram import F
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select
from bot.database.models import User, WeatherData
from bot.database.database import async_session
from bot.services.weather_api import WeatherAPI
from bot.services.analytics import WeatherAnalytics
from bot.keyboards.reply import get_weather_keyboard, get_start_keyboard


logger = logging.getLogger(__name__)
weather_api = WeatherAPI()


async def get_weather_now(message: types.Message) -> None:
    """Получение текущей информации о погоде"""
    user_id = message.from_user.id

    # получение данных о пользователе
    async with async_session() as session:
        stmt = select(User).where(User.user_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

    if not user:
        await message.answer("Вы еще не зарегистрированы. Пожалуйста, зарегистрируйтесь, чтобы получать прогноз погоды",
                             reply_markup=get_start_keyboard(is_registered=False)
                             )
        return

    # получение данных о погоде для города, который был выбран пользователем
    weather_data = await weather_api.get_current_weather(user.city)

    if not weather_data:
        await message.answer("Извините, ошибка получения данных о погоде. Попробуйте позже",
                             reply_markup=get_weather_keyboard()
                             )
        return

    # сохранение данных о погоде в базу данных
    async with async_session() as session:
        new_weather_data = WeatherData(
            user_id=user.id,
            temperature=weather_data["temperature"],
            feels_like=weather_data["feels_like"],
            pressure=weather_data["pressure"],
            humidity=weather_data["humidity"],
            wind_speed=weather_data["wind_speed"],
            description=weather_data["description"]
        )
        session.add(new_weather_data)
        await session.commit()

    # ответное сообщение с текущей погодой пользователю
    weather_message = (
        f"Погода в городе {weather_data['city']} ({weather_data['country']}):\n\n"
        f"🌡️ Температура: {weather_data['temperature']:.1f}°C (ощущается как {weather_data['feels_like']:.1f}°C)\n"
        f"💧 Влажность: {weather_data['humidity']}%\n"
        f"🌬️ Ветер: {weather_data['wind_speed']} м/с\n"
        f"🔍 {weather_data['description'].capitalize()}\n\n"
        f"🕒 Данные обновлены: {message.date.strftime('%H:%M:%S')}"
    )

    await message.answer(weather_message, reply_markup=get_weather_keyboard())

async def get_weather_forecast(message: types.Message) -> None:
    """Получение прогноза погоды на 5 дней"""
    user_id = message.from_user.id

    # получение данных о пользователе
    async with async_session() as session:
        stmt = select(User).where(User.user_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

    if not user:
        await message.answer("Вы еще не зарегистрированы. Пожалуйста, зарегистрируйтесь, чтобы получать прогноз погоды",
                             reply_markup=get_start_keyboard(is_registered=False)
                             )
        return
    # получение прогноза погоды для города, который был выбран пользователем
    forecast_data = await weather_api.get_weather_forecast(user.city, days=5)

    if not forecast_data:
        await message.answer("Извините, ошибка получения данных о погоде. Попробуйте позже",
                             reply_markup=get_weather_keyboard()
                             )
        return

    # ответное сообщение с прогнозом погоды пользователю
    forecast_message = f"Прогноз погоды на 5 дней для города {forecast_data['city']} ({forecast_data['country']}):\n\n"

    for forecast in forecast_data["forecasts"][:5]:  # Берем только первые 5 дней
        date_str = forecast["date"].strftime("%d.%m")
        forecast_message += (
            f"📅 {date_str}:\n"
            f"🌡️ Температура: {forecast['avg_temp']:.1f}°C (от {forecast['min_temp']:.1f}°C до {forecast['max_temp']:.1f}°C)\n"
            f"💧 Влажность: {forecast['avg_humidity']:.0f}%\n"
            f"🌬️ Ветер: {forecast['avg_wind']:.1f} м/с\n"
            f"🔍 {forecast['description'].capitalize()}\n\n"
        )
    await message.answer(forecast_message, reply_markup=get_weather_keyboard())

async def get_weekly_analysis(message: types.Message) -> None:
    """Получение недельного анализа погоды"""
    user_id = message.from_user.id

    # Получение данных о пользователе
    async with async_session() as session:
        stmt = select(User).where(User.user_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

    if not user:
        await message.answer("Вы еще не зарегистрированы. Пожалуйста, зарегистрируйтесь, чтобы получать прогноз погоды",
                             reply_markup=get_start_keyboard(is_registered=False)
                             )
        return

    # Получение еженедельного анализа погоды
    analysis_data = await WeatherAnalytics().get_weekly_analysis(user.id)

    if not analysis_data:
        await message.answer(
            "Извините, не удалось получить анализ погоды. Возможно, недостаточно данных для анализа. "
            "Попробуй позже, когда будет собрано больше данных.",
            reply_markup=get_weather_keyboard()
        )
        return

    # формирование сообщения с еженедельным анализом погоды
    start_date = analysis_data["period"]["start"].strftime("%d.%m")
    end_date = analysis_data["period"]["end"].strftime("%d.%m")

    analysis_message = f"Анализ погоды за период {start_date} - {end_date} для города {analysis_data['city']}:\n\n"

    # информация о тенденциях температуры, влажности и ветра
    if analysis_data["trends"]:
        analysis_message += "📊 Тенденции за неделю:\n"
        analysis_message += f"🌡️ Температура: {analysis_data['trends']['temperature']['description']} "
        analysis_message += f"({analysis_data['trends']['temperature']['value']:.1f}°C)\n"
        analysis_message += f"💧 Влажность: {analysis_data['trends']['humidity']['description']} "
        analysis_message += f"({analysis_data['trends']['humidity']['value']:.1f}%)\n"
        analysis_message += f"🌬️ Ветер: {analysis_data['trends']['wind']['description']} "
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

async def change_city(message: types.Message):
    """Смена города"""
    from bot.handlers.registration import register_command
    await register_command(message, FSMContext(message.bot.state_storage, message.chat.id, message.from_user.id))

def register_weather_handlers(dp: Dispatcher):
    """Регистрация обработчиков команд для погоды"""
    dp.message.register(get_weather_now, F.text.casefold() == "Погода сейчас")
    dp.message.register(get_weather_forecast, F.text.casefold() == "Прогноз погоды на 5 дней")
    dp.message.register(get_weekly_analysis, F.text.casefold == "Еженедельный анализ погоды")
    dp.message.register(change_city, F.text.casefold()=="Изменить город")

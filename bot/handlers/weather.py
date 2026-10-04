import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

from aiogram import Dispatcher, F, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext

from bot.handlers.texts import CITY_NOT_FOUND_SAVED, SERVICE_UNAVAILABLE
from bot.keyboards.inline import get_forecast_keyboard
from bot.keyboards.reply import get_start_keyboard, get_weather_keyboard
from bot.services.analytics import WeatherAnalytics
from bot.services.messages import (
    format_current_weather,
    format_forecast,
    format_weekly_analysis,
)
from bot.services.users import get_user_by_telegram_id, update_timezone_offset
from bot.services.weather_api import CityNotFoundError, WeatherAPIError, weather_api

logger = logging.getLogger(__name__)

PERIOD_TITLES = {
    "tomorrow": "Прогноз погоды на завтра",
    "3days": "Прогноз погоды на 3 дня",
    "5days": "Прогноз погоды на 5 дней",
}


def _api_error_text(error: WeatherAPIError) -> str:
    """Что ответить человеку, если OpenWeather не дал данных."""
    if isinstance(error, CityNotFoundError):
        return CITY_NOT_FOUND_SAVED
    return SERVICE_UNAVAILABLE


def select_forecast_days(
    forecasts: list[dict[str, Any]], period: str, today: date
) -> list[dict[str, Any]]:
    """Дни прогноза для выбранного периода.
    today - сегодняшняя дата по времени города. Периоды: tomorrow, 3days, 5days."""
    if period == "tomorrow":
        tomorrow = today + timedelta(days=1)
        return [f for f in forecasts if f["date"] == tomorrow]
    if period == "3days":
        return forecasts[:3]
    if period == "5days":
        return forecasts[:5]
    raise ValueError(f"Неизвестный период прогноза: {period}")


async def get_weather_now(message: types.Message):
    """Получение текущей информации о погоде"""
    if message.from_user is None:
        return

    # получение данных о пользователе
    user = await get_user_by_telegram_id(message.from_user.id)

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

    await update_timezone_offset(user.id, weather_data["timezone"])

    # ответное сообщение с текущей погодой пользователю
    weather_message = format_current_weather(
        weather_data, int(message.date.timestamp())
    )
    await message.answer(weather_message, reply_markup=get_weather_keyboard())


async def get_weather_forecast(message: types.Message) -> None:
    """Получение прогноза погоды на 5 дней"""
    if message.from_user is None:
        return
    try:
        # получение данных о пользователе
        user = await get_user_by_telegram_id(message.from_user.id)

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
        forecast_message = format_forecast(
            forecast_data, forecast_data["forecasts"][:5], "Прогноз погоды на 5 дней"
        )
        await message.answer(forecast_message, reply_markup=get_forecast_keyboard())
    except WeatherAPIError as e:
        await message.answer(_api_error_text(e), reply_markup=get_weather_keyboard())
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer("Произошла внутренняя ошибка при получении прогноза.")


async def on_forecast_period(callback: types.CallbackQuery) -> None:
    """Нажатие кнопки периода под прогнозом: правим то же сообщение."""
    message = callback.message
    if callback.data is None or not isinstance(message, types.Message):
        await callback.answer()
        return
    period = callback.data.removeprefix("forecast:")
    if period != "now" and period not in PERIOD_TITLES:
        await callback.answer()
        return

    user = await get_user_by_telegram_id(callback.from_user.id)

    if not user:
        await callback.answer(
            "Вы еще не зарегистрированы. Нажмите /start", show_alert=True
        )
        return

    now_utc = datetime.now(UTC)
    try:
        if period == "now":
            weather_data = await weather_api.get_current_weather(user.city)
            text = format_current_weather(weather_data, int(now_utc.timestamp()))
        else:
            forecast_data = await weather_api.get_forecast(user.city, days=5)
            today = (now_utc + timedelta(seconds=user.timezone_offset)).date()
            days = select_forecast_days(forecast_data["forecasts"], period, today)
            if days:
                text = format_forecast(forecast_data, days, PERIOD_TITLES[period])
            else:
                text = "Для выбранного периода прогноза пока нет."
    except WeatherAPIError as e:
        await callback.answer(_api_error_text(e), show_alert=True)
        return

    try:
        await message.edit_text(text, reply_markup=get_forecast_keyboard())
    except TelegramBadRequest as e:
        # та же кнопка нажата повторно: текст не изменился, это не ошибка
        if "message is not modified" not in e.message:
            raise
    await callback.answer()


async def get_weekly_analysis(message: types.Message) -> None:
    """Получение недельного анализа погоды"""
    if message.from_user is None:
        return
    # Получение данных о пользователе
    user = await get_user_by_telegram_id(message.from_user.id)

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

    await message.answer(
        format_weekly_analysis(analysis_data), reply_markup=get_weather_keyboard()
    )


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
    dp.callback_query.register(on_forecast_period, F.data.startswith("forecast:"))

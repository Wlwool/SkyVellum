from aiogram import Dispatcher
from bot.handlers.start import register_start_handlers
from bot.handlers.registration import register_registration_handlers
from bot.handlers.weather import register_weather_handlers
from bot.handlers.admin import register_admin_handlers


def register_all_handlers(dp: Dispatcher):
    """Регистрирует все обработчики."""
    register_start_handlers(dp)
    register_registration_handlers(dp)
    register_weather_handlers(dp)
    register_admin_handlers(dp)
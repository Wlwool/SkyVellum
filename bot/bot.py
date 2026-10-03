import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config.config import Config
from bot.handlers import register_all_handlers
from bot.services.weather_api import weather_api
from bot.utils.logger import setup_logger
from bot.utils.scheduler import schedule_jobs


async def main():
    setup_logger()
    logger = logging.getLogger(__name__)
    logger.info("Запуск бота...")

    config = Config()
    config.validate()

    # Инициализация бота и диспетчера
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрация хэндлеров
    register_all_handlers(dp)

    # Запуск и настройка асинхронного планировщика
    scheduler = AsyncIOScheduler()
    schedule_jobs(scheduler, bot)

    scheduler.start()

    # Запуск бота
    logger.info("Бот запущен!")
    try:
        await dp.start_polling(bot)
    finally:
        # сначала планировщик: идущая задача не должна открыть новую сессию
        scheduler.shutdown(wait=False)
        await weather_api.close()

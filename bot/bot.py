import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config.config import Config
from bot.utils.logger import setup_logger
from bot.database.database import setup_db
from bot.handlers import register_all_handlers
from bot.utils.scheduler import schedule_jobs


async def main():
    setup_logger()
    logger = logging.getLogger(__name__)
    logger.info("Запуск бота...")

    config = Config()

    # Инициализация бота и диспетчера
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Запуск базы данных
    await setup_db()

    # Регистрация хэндлеров
    register_all_handlers(dp)

    # Запуск и настройка асинхронного планировщика
    scheduler = AsyncIOScheduler()
    schedule_jobs(scheduler, bot)

    scheduler.start()

    # Запуск бота
    logger.info("Бот запущен!")
    await dp.start_polling(bot)

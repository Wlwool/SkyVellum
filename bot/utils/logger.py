import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger():
    """Логирование для бота"""
    os.makedirs("logs", exist_ok=True)  # создает папку для логов, если она не существует

    # настройка логгера
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # форматирование логов
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # обработчик для файла логов
    file_handler = RotatingFileHandler("logs/bot.log",
                                       maxBytes=10485760,
                                       backupCount=5)  # размер файла 10 МБ
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # добавление обработчиков в логгер
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # добавление уровня логирования для некоторых модулей
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)






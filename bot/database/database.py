"""
Модуль для работы с базой данных бота.

Содержит:
- Базовый класс для моделей SQLAlchemy
- Настройки асинхронного подключения к БД
- Утилиты для управления подключением
"""

import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from bot.config.config import Config


logger = logging.getLogger(__name__)
config = Config()


Base = declarative_base()  # базовый класс для моделей данных

# Создаем асинхронный движок и сессию для работы с базой данных
engine = create_async_engine(config.DB_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def setup_db():
    """Инициализация структуры базы данных при запуске бота.

    Выполняет:
    - Создание всех таблиц, определенных в моделях
    - Проверку подключения к БД
    - Логирование процесса инициализации
    """
    from bot.database.models import User, WeatherData
    async with engine.begin() as conn:
        logger.info("Создание таблиц в базе данных")
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Подключение к базе данных завершено")

async def get_session() -> AsyncSession:
    """
    Генератор асинхронных сессий для работы с БД.

    Возвращает:
        AsyncSession: Асинхронная сессия SQLAlchemy

    Особенности:
    - Автоматически закрывает сессию после использования
    - Поддерживает async context manager
    """
    async with async_session() as session:
        yield session

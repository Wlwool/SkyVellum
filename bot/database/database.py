"""
Модуль для работы с базой данных бота.

Содержит:
- Базовый класс для моделей SQLAlchemy
- Настройки асинхронного подключения к БД
- Генератор асинхронных сессий
Схема БД создаётся и меняется миграциями Alembic
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from bot.config.config import Config

config = Config()


class Base(DeclarativeBase):
    """Базовый класс для моделей данных."""


# Создает асинхронный движок и сессию для работы с БД
engine = create_async_engine(config.DB_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """
    Генератор асинхронных сессий для работы с БД.

    Возвращает:
        AsyncSession: Асинхронная сессия SQLAlchemy

    - Автоматически закрывает сессию после использования
    - Поддерживает async context manager
    """
    async with async_session() as session:
        yield session

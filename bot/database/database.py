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
    """Настройка базы данных при запуске бота"""
    from bot.database.models import User, WeatherData
    async with engine.begin() as conn:
        logger.info("Создание таблиц в базе данных")
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Подключение к базе данных завершено")

async def get_session() -> AsyncSession:
    """Возвращает сессию для работы с базой данных"""
    async with async_session() as session:
        yield session

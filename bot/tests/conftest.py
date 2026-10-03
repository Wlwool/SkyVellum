import atexit
import os
import shutil
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

_tmp_dir = tempfile.mkdtemp(prefix="skyvellum_tests_")
atexit.register(shutil.rmtree, _tmp_dir, ignore_errors=True)

os.environ["BOT_TOKEN"] = "123456:test-token"
os.environ["WEATHER_API_KEY"] = "test-key"
os.environ["DB_URL"] = f"sqlite+aiosqlite:///{Path(_tmp_dir) / 'test.db'}"
os.environ["ADMIN_IDS"] = ""


@pytest_asyncio.fixture
async def db():
    """Чистая схема БД на каждый тест."""
    import bot.database.models  # noqa: F401
    from bot.database.database import Base, engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def make_user(db):
    """Фабрика пользователей. Возвращает внутренний User.id."""
    from bot.database.database import async_session
    from bot.database.models import User

    async def _make(
        user_id: int = 123456,
        city: str = "Москва",
        is_active: bool = True,
        timezone_offset: int = 0,
    ) -> int:
        async with async_session() as session:
            user = User(
                user_id=user_id,
                city=city,
                is_active=is_active,
                timezone_offset=timezone_offset,
            )
            session.add(user)
            await session.commit()
            return user.id

    return _make

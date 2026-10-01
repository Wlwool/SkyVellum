from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlalchemy import select

from bot.database.database import async_session
from bot.database.models import User
from bot.handlers.start import cmd_start


async def test_start_reactivates_returning_user(make_user):
    """Пользователь, разблокировавший бота, снова становится активным."""
    await make_user(user_id=123456, is_active=False)
    message = AsyncMock()
    message.from_user = SimpleNamespace(id=123456, first_name="Анна")

    await cmd_start(message)

    async with async_session() as session:
        result = await session.execute(
            select(User.is_active).where(User.user_id == 123456)
        )
        assert result.scalar_one() is True

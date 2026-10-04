from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers import admin

ADMIN_ID = 1
STRANGER_ID = 2


def _message(user_id: int | None) -> MagicMock:
    """Подделка сообщения Telegram: автор (или его отсутствие) и метод answer."""
    message = MagicMock()
    message.from_user = None if user_id is None else SimpleNamespace(id=user_id)
    message.answer = AsyncMock()
    return message


def _as_admin():
    """Подменяет config в модуле admin: админом считается только ADMIN_ID."""
    return patch.object(admin, "config", SimpleNamespace(ADMIN_IDS=[ADMIN_ID]))


async def test_stats_denied_for_non_admin(make_user):
    """Не админ получает отказ и никакой статистики."""
    await make_user(user_id=111)
    message = _message(STRANGER_ID)

    with _as_admin():
        await admin.cmd_stats(message)

    message.answer.assert_awaited_once()
    text = message.answer.call_args.args[0]
    assert "нет прав" in text
    assert "Всего пользователей" not in text


async def test_stats_counts_users_and_cities(make_user):
    """Админ видит всего и активных пользователей, города по убыванию."""
    await make_user(user_id=111, city="Москва")
    await make_user(user_id=222, city="Москва")
    await make_user(user_id=333, city="Тамбов", is_active=False)
    message = _message(ADMIN_ID)

    with _as_admin():
        await admin.cmd_stats(message)

    message.answer.assert_awaited_once()
    text = message.answer.call_args.args[0]
    assert "Всего пользователей: 3" in text
    assert "Активных пользователей: 2" in text
    assert "- Москва: 2 пользователей" in text
    assert "- Тамбов: 1 пользователей" in text
    assert text.index("Москва") < text.index("Тамбов")


async def test_stats_ignores_message_without_author():
    """Сообщение без автора (например, из канала): молча выходим."""
    message = _message(None)

    with _as_admin():
        await admin.cmd_stats(message)

    message.answer.assert_not_awaited()

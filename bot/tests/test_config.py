from bot.config.config import Config


def test_config_reads_environment_at_creation(monkeypatch):
    """Config должен читать переменные при создании, а не при импорте."""
    monkeypatch.setenv("BOT_TOKEN", "another-token")
    assert Config().BOT_TOKEN == "another-token"


def test_db_url_default_uses_async_driver(monkeypatch):
    """Дефолт DB_URL должен подходить для асинхронного движка."""
    monkeypatch.delenv("DB_URL", raising=False)
    assert Config().DB_URL == "sqlite+aiosqlite:///database/weather_bot.db"


def test_admin_ids_are_parsed(monkeypatch):
    monkeypatch.setenv("ADMIN_IDS", "1,2")
    assert Config().ADMIN_IDS == [1, 2]

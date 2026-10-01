import pytest

from bot.config.config import Config


def test_validate_passes_with_required_vars(monkeypatch):
    """Токен и ключ погоды заданы: проверка проходит."""
    monkeypatch.setenv("BOT_TOKEN", "123:abc")
    monkeypatch.setenv("WEATHER_API_KEY", "key")

    Config().validate()


def test_validate_reports_all_missing_vars(monkeypatch):
    """Не заданы обе переменные: в сообщении названы обе сразу."""
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.delenv("WEATHER_API_KEY", raising=False)

    with pytest.raises(ValueError) as exc_info:
        Config().validate()

    assert "BOT_TOKEN" in str(exc_info.value)
    assert "WEATHER_API_KEY" in str(exc_info.value)


def test_validate_reports_only_missing_var(monkeypatch):
    """Не задан только ключ погоды: токен в сообщении не упоминается."""
    monkeypatch.setenv("BOT_TOKEN", "123:abc")
    monkeypatch.delenv("WEATHER_API_KEY", raising=False)

    with pytest.raises(ValueError) as exc_info:
        Config().validate()

    assert "WEATHER_API_KEY" in str(exc_info.value)
    assert "BOT_TOKEN" not in str(exc_info.value)

import datetime
from unittest.mock import AsyncMock, patch

import pytest

from bot.services.analytics import WeatherAnalytics
from bot.utils import scheduler


@pytest.fixture(autouse=True)
def no_sleep():
    """Рассылка делает asyncio.sleep(0.5) на пользователя: в тестах не ждём."""
    with patch("bot.utils.scheduler.asyncio.sleep", new=AsyncMock()):
        yield


def _analysis() -> dict:
    return {
        "city": "Москва",
        "past_week": {
            "period": {
                "start": datetime.date(2026, 4, 1),
                "end": datetime.date(2026, 4, 7),
            },
            "trends": {
                "temperature": {"description": "повышение", "value": 5.0},
                "humidity": {"description": "понижение", "value": -5.0},
                "wind": {"description": "ослабление", "value": -2.5},
            },
        },
        "next_week_forecast": {
            "daily_forecasts": [
                {
                    "date": datetime.date(2026, 4, 8),
                    "avg_temp": 16.0,
                    "min_temp": 12.0,
                    "max_temp": 20.0,
                    "avg_humidity": 55.0,
                    "avg_wind": 2.8,
                    "description": "переменная облачность",
                }
            ],
            "summary": {
                "avg_temp": 16.5,
                "min_temp": 11.0,
                "max_temp": 21.0,
                "avg_humidity": 58.0,
                "avg_wind": 3.0,
            },
            "days_count": 1,
        },
    }


def _patch_analysis(return_value):
    return patch.object(
        WeatherAnalytics,
        "get_weekly_analysis_with_forecast",
        new=AsyncMock(return_value=return_value),
    )


async def test_send_weekly_analysis_success(make_user):
    """Активный пользователь получает сообщение с анализом и прогнозом."""
    await make_user(user_id=123456)
    bot = AsyncMock()

    with _patch_analysis(_analysis()):
        await scheduler.send_weekly_analysis(bot=bot)

    bot.send_message.assert_awaited_once()
    chat_id, text = bot.send_message.call_args.args
    assert chat_id == 123456
    assert "Москва" in text
    assert "01.04 - 07.04" in text
    assert "Прогноз на следующую неделю" in text


async def test_send_weekly_analysis_no_data(make_user):
    """Если анализа нет (None), сообщение не отправляется."""
    await make_user(user_id=123456)
    bot = AsyncMock()

    with _patch_analysis(None):
        await scheduler.send_weekly_analysis(bot=bot)

    bot.send_message.assert_not_called()


async def test_send_weekly_analysis_user_inactive(make_user):
    """Неактивные пользователи не получают рассылку."""
    await make_user(user_id=123456, is_active=False)
    bot = AsyncMock()

    with _patch_analysis(_analysis()):
        await scheduler.send_weekly_analysis(bot=bot)

    bot.send_message.assert_not_called()


async def test_send_weekly_analysis_exception_handling(make_user):
    """Ошибка отправки одному пользователю логируется и не рвёт рассылку."""
    await make_user(user_id=111)
    await make_user(user_id=222)
    bot = AsyncMock()
    bot.send_message.side_effect = [Exception("API Error"), None]

    with (
        _patch_analysis(_analysis()),
        patch.object(scheduler.logger, "error") as mock_log_error,
    ):
        await scheduler.send_weekly_analysis(bot=bot)

    assert bot.send_message.await_count == 2
    mock_log_error.assert_called_once()
    assert "API Error" in str(mock_log_error.call_args)

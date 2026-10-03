import datetime
from unittest.mock import AsyncMock, patch

import pytest
from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import SendMessage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from bot.database.database import async_session
from bot.database.models import User
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


def _forbidden() -> TelegramForbiddenError:
    """Ошибка Telegram «бот заблокирован пользователем»."""
    return TelegramForbiddenError(
        method=SendMessage(chat_id=1, text="x"),
        message="Forbidden: bot was blocked by the user",
    )


def _send_failing_for(chat_id_to_fail: int, error: Exception) -> AsyncMock:
    """send_message, который бросает error только для одного chat_id."""

    async def _send(chat_id, text):
        if chat_id == chat_id_to_fail:
            raise error

    return AsyncMock(side_effect=_send)


async def _is_active(user_id: int) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(User.is_active).where(User.user_id == user_id)
        )
        return bool(result.scalar_one())


def _weather() -> dict:
    return {
        "city": "Москва",
        "temperature": 10.0,
        "feels_like": 8.0,
        "humidity": 70,
        "wind_speed": 3.0,
        "description": "ясно",
        "timezone": 10800,
    }


async def test_weekly_blocked_user_is_deactivated(make_user):
    """Заблокировавший бота пользователь деактивируется, остальные получают."""
    await make_user(user_id=111)
    await make_user(user_id=222)
    bot = AsyncMock()
    bot.send_message = _send_failing_for(111, _forbidden())

    with _patch_analysis(_analysis()):
        await scheduler.send_weekly_analysis(bot=bot)

    assert bot.send_message.await_count == 2
    assert await _is_active(111) is False
    assert await _is_active(222) is True


async def test_weekly_generic_error_keeps_user_active(make_user):
    """Временный сбой (не Forbidden) не должен отключать пользователя."""
    await make_user(user_id=111)
    bot = AsyncMock()
    bot.send_message = _send_failing_for(111, Exception("API Error"))

    with _patch_analysis(_analysis()):
        await scheduler.send_weekly_analysis(bot=bot)

    assert await _is_active(111) is True


async def test_daily_blocked_user_is_deactivated(make_user):
    """То же для ежедневной рассылки."""
    await make_user(user_id=111)
    await make_user(user_id=222)
    bot = AsyncMock()
    bot.send_message = _send_failing_for(111, _forbidden())

    with (
        patch.object(
            scheduler.weather_api,
            "get_current_weather",
            new=AsyncMock(return_value=_weather()),
        ),
        patch.object(
            WeatherAnalytics,
            "save_weather_data_for_week_analysis",
            new=AsyncMock(),
        ),
    ):
        await scheduler.send_daily_weather(bot=bot)

    assert bot.send_message.await_count == 2
    assert await _is_active(111) is False
    assert await _is_active(222) is True


async def _timezone_offset(user_id: int) -> int:
    async with async_session() as session:
        result = await session.execute(
            select(User.timezone_offset).where(User.user_id == user_id)
        )
        return int(result.scalar_one())


async def test_daily_updates_timezone_offset(make_user):
    """Утренняя рассылка подтягивает смещение пояса из ответа OpenWeather."""
    await make_user(user_id=111)
    bot = AsyncMock()
    weather = {**_weather(), "timezone": 25200}

    with (
        patch.object(
            scheduler.weather_api,
            "get_current_weather",
            new=AsyncMock(return_value=weather),
        ),
        patch.object(
            WeatherAnalytics,
            "save_weather_data_for_week_analysis",
            new=AsyncMock(),
        ),
    ):
        await scheduler.send_daily_weather(bot=bot)

    assert await _timezone_offset(111) == 25200


async def _load_users(*user_ids: int) -> list[User]:
    """Загружает пользователей по Telegram ID (объекты читаются и после сессии)."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.user_id.in_(user_ids)))
        return list(result.scalars().all())


async def test_weekly_sends_only_to_given_users(make_user):
    """Если передан список получателей, остальные активные ничего не получают."""
    await make_user(user_id=111)
    await make_user(user_id=222)
    bot = AsyncMock()
    users = await _load_users(222)

    with _patch_analysis(_analysis()):
        await scheduler.send_weekly_analysis(bot=bot, users=users)

    bot.send_message.assert_awaited_once()
    assert bot.send_message.call_args.args[0] == 222


async def test_daily_sends_only_to_given_users(make_user):
    """То же для ежедневной рассылки."""
    await make_user(user_id=111)
    await make_user(user_id=222)
    bot = AsyncMock()
    users = await _load_users(222)

    with (
        patch.object(
            scheduler.weather_api,
            "get_current_weather",
            new=AsyncMock(return_value=_weather()),
        ),
        patch.object(
            WeatherAnalytics,
            "save_weather_data_for_week_analysis",
            new=AsyncMock(),
        ),
    ):
        await scheduler.send_daily_weather(bot=bot, users=users)

    bot.send_message.assert_awaited_once()
    assert bot.send_message.call_args.args[0] == 222


def _user(user_id: int, offset: int) -> User:
    return User(user_id=user_id, city="Москва", timezone_offset=offset)


def test_select_due_users_filters_by_local_time():
    """05:00 UTC: у москвича (+3 ч) 08:00, у пользователя с нулевым смещением нет."""
    now = datetime.datetime(2026, 9, 21, 5, 0, tzinfo=datetime.UTC)
    moscow, utc = _user(1, 10800), _user(2, 0)

    assert scheduler.select_due_users([moscow, utc], now, hour=8) == [moscow]


def test_select_due_users_respects_weekday():
    """Воскресная рассылка: в воскресенье в 12:00 по Москве да, в понедельник нет."""
    sunday = datetime.datetime(2026, 9, 27, 9, 0, tzinfo=datetime.UTC)
    monday = datetime.datetime(2026, 9, 28, 9, 0, tzinfo=datetime.UTC)
    moscow = _user(1, 10800)

    assert scheduler.select_due_users([moscow], sunday, 12, weekday=6) == [moscow]
    assert scheduler.select_due_users([moscow], monday, 12, weekday=6) == []


async def test_tick_sends_daily_to_users_at_local_eight(make_user):
    """Тик в 05:00 UTC: утренняя рассылка идёт только москвичу."""
    await make_user(user_id=111, timezone_offset=10800)
    await make_user(user_id=222, timezone_offset=0)
    bot = AsyncMock()
    now = datetime.datetime(2026, 9, 21, 5, 0, tzinfo=datetime.UTC)

    with (
        patch.object(scheduler, "send_daily_weather", new=AsyncMock()) as daily,
        patch.object(scheduler, "send_weekly_analysis", new=AsyncMock()) as weekly,
    ):
        await scheduler.send_due_broadcasts(bot, now_utc=now)

    daily.assert_awaited_once()
    assert [u.user_id for u in daily.await_args_list[0].args[1]] == [111]
    weekly.assert_not_awaited()


async def test_tick_sends_weekly_on_local_sunday_noon(make_user):
    """Тик в воскресенье 09:00 UTC: у москвича 12:00, уходит только анализ недели."""
    await make_user(user_id=111, timezone_offset=10800)
    bot = AsyncMock()
    now = datetime.datetime(2026, 9, 27, 9, 0, tzinfo=datetime.UTC)

    with (
        patch.object(scheduler, "send_daily_weather", new=AsyncMock()) as daily,
        patch.object(scheduler, "send_weekly_analysis", new=AsyncMock()) as weekly,
    ):
        await scheduler.send_due_broadcasts(bot, now_utc=now)

    weekly.assert_awaited_once()
    assert [u.user_id for u in weekly.await_args_list[0].args[1]] == [111]
    daily.assert_not_awaited()


async def test_tick_skips_inactive_and_not_due_users(make_user):
    """Неактивных и тех, у кого не их время, рассылки не получают вовсе."""
    await make_user(user_id=111, is_active=False, timezone_offset=10800)
    await make_user(user_id=222, timezone_offset=0)
    bot = AsyncMock()
    now = datetime.datetime(2026, 9, 21, 5, 0, tzinfo=datetime.UTC)

    with (
        patch.object(scheduler, "send_daily_weather", new=AsyncMock()) as daily,
        patch.object(scheduler, "send_weekly_analysis", new=AsyncMock()) as weekly,
    ):
        await scheduler.send_due_broadcasts(bot, now_utc=now)

    daily.assert_not_awaited()
    weekly.assert_not_awaited()


async def test_schedule_jobs_registers_single_tick():
    """Вместо двух фиксированных заданий регистрируется одно - тик."""
    sched = AsyncIOScheduler()
    scheduler.schedule_jobs(sched, AsyncMock())

    assert [job.id for job in sched.get_jobs()] == ["due_broadcasts"]

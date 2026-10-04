import asyncio
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.database.models import User
from bot.services.analytics import WeatherAnalytics
from bot.services.messages import format_daily_weather, format_weekly_broadcast
from bot.services.users import get_active_users, set_user_active, update_timezone_offset
from bot.services.weather_api import WeatherAPIError, weather_api
from bot.utils.timeutils import is_local_time_due

logger = logging.getLogger(__name__)


DAILY_HOUR = 8  # местное время утренней рассылки
WEEKLY_HOUR = 12  # местное время воскресной рассылки
SUNDAY = 6  # datetime.weekday(): понедельник = 0
TICK_MINUTES = 15  # шаг планировщика = ширина окна в is_local_time_due


async def send_daily_weather(bot: Bot, users: Sequence[User] | None = None):
    """Отправляет ежедневный прогноз погоды.
    users - кому слать, если не задан, то всем активным пользователям
    """
    logger.info("Запуск рассылки ежедневного прогноза погоды")

    if users is None:
        users = await get_active_users()

    for user in users:
        try:
            # получение прогноза погоды для города пользователя
            weather_data: dict[str, Any] = await weather_api.get_current_weather(
                user.city
            )
            await update_timezone_offset(
                user.id,
                weather_data["timezone"],
            )

            # сохранение данных о погоде для еженедельного анализа
            await WeatherAnalytics.save_weather_data_for_week_analysis(
                user.id,
                weather_data,
            )

            # отправка сообщения пользователю
            await bot.send_message(user.user_id, format_daily_weather(weather_data))
            logger.info(f"Отправлен прогноз погоды для пользователя {user.user_id}")

            # небольшая задержка, чтобы избежать слишком частых запросов к API
            await asyncio.sleep(0.5)

        except WeatherAPIError as e:
            logger.warning(
                f"Не удалось получить погоду для пользователя {user.user_id}, "
                f"город: {user.city}: {e}"
            )
        except TelegramForbiddenError:
            logger.warning(
                f"Пользователь {user.user_id} заблокировал бота, деактивируем"
            )
            await set_user_active(user.id, False)
        except Exception as e:
            logger.error(
                f"Ошибка при отправке прогноза погоды пользователю {user.user_id}: {e}"
            )


async def send_weekly_analysis(bot: Bot, users: Sequence[User] | None = None):
    """Отправляет еженедельный анализ погоды.
    users - кому слать, если не задан, то всем активным пользователям.
    """
    logger.info("Запуск рассылки еженедельного анализа погоды")

    if users is None:
        users = await get_active_users()

    for user in users:
        try:
            # получение анализа погоды за неделю
            # (прошлая неделя и прогноз на следующие 5 дней)
            analysis_data = await WeatherAnalytics.get_weekly_analysis_with_forecast(
                user.id,
                weather_api,
            )

            if not analysis_data:
                logger.warning(
                    f"Не удалось получить еженедельный анализ погоды "
                    f"для пользователя {user.user_id}"
                )
                continue

            # Отправляем сообщение пользователю
            await bot.send_message(user.user_id, format_weekly_broadcast(analysis_data))
            logger.info(
                f"Отправлен еженедельный анализ погоды пользователю {user.user_id}"
            )
            await asyncio.sleep(0.5)

        except TelegramForbiddenError:
            logger.warning(
                f"Пользователь {user.user_id} заблокировал бота, деактивируем"
            )
            await set_user_active(user.id, False)
        except Exception as e:
            logger.error(
                f"Ошибка при отправке еженедельного анализа "
                f"пользователю {user.user_id}: {e}"
            )


def select_due_users(
    users: Sequence[User],
    now_utc: datetime,
    hour: int,
    weekday: int | None = None,
) -> list[User]:
    """Кому сейчас пора слать: местное время hour:00 (и день недели weekday)."""
    return [
        user
        for user in users
        if is_local_time_due(now_utc, user.timezone_offset, hour, weekday, TICK_MINUTES)
    ]


async def send_due_broadcasts(bot: Bot, now_utc: datetime | None = None) -> None:
    """Тик планировщика (раз в TICK_MINUTES минут).
    Отправляет утренний прогноз тем, у кого сейчас 8:00 по местному времени,
    и еженедельный анализ тем, у кого сейчас воскресенье 12:00.
    now_utc нужен тестам; в работе берётся текущее время.
    """
    if now_utc is None:
        now_utc = datetime.now(UTC)
    users = await get_active_users()

    daily = select_due_users(users, now_utc, DAILY_HOUR)
    if daily:
        await send_daily_weather(bot, daily)

    weekly = select_due_users(users, now_utc, WEEKLY_HOUR, SUNDAY)
    if weekly:
        await send_weekly_analysis(bot, weekly)


def schedule_jobs(scheduler: AsyncIOScheduler, bot: Bot):
    """Настройка планировщика заданий.
    Раз в TICK_MINUTES минут проверяется, у кого наступило местное время рассылки:
    ежедневный прогноз в 8:00, еженедельный анализ в воскресенье в 12:00.
    """
    scheduler.add_job(
        send_due_broadcasts,
        trigger=CronTrigger(minute=f"*/{TICK_MINUTES}"),
        kwargs={"bot": bot},
        id="due_broadcasts",
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info(
        f"Настроена проверка рассылок каждые {TICK_MINUTES} минут "
        f"(прогноз в {DAILY_HOUR}:00, анализ в воскресенье в {WEEKLY_HOUR}:00 "
        f"по местному времени)"
    )

import logging
import asyncio
from sqlalchemy.future import select
from aiogram import Bot
from typing import Any
from datetime import datetime, time, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from bot.database.models import User
from bot.database.database import async_session
from bot.services.weather_api import WeatherAPI
from bot.services.analytics import WeatherAnalytics


logger = logging.getLogger(__name__)
weather_api = WeatherAPI()


async def send_daily_weather(bot: Bot):
    """Отправляет ежедневный прогноз погоды всем пользователям"""
    logger.info("Запуск рассылки ежедневного прогноза погоды")

    async with async_session() as session:
        stmt = select(User).where(User.is_active == True)  # type: ignore
        result = await session.execute(stmt)
        users = result.scalars().all()

    for user in users:
        try:
            # получение прогноза погоды для города пользователя
            weather_data: dict[str, Any] | None = await weather_api.get_current_weather(user.city)

            if not weather_data:
                logger.warning(f"Не удалось получить погоду для пользователя {user.user_id}, город: {user.city}")
                continue

            # формирование сообщения с прогнозом погоды
            message = (
                f"☀️ Доброе утро! Вот прогноз погоды на сегодня для города {weather_data['city']}:\n\n"
                f"🌡️ Температура: {weather_data['temperature']:.1f}°C (ощущается как {weather_data['feels_like']:.1f}°C)\n"
                f"💧 Влажность: {weather_data['humidity']}%\n"
                f"🌬️ Ветер: {weather_data['wind_speed']} м/с\n"
                f"🔍 {weather_data['description'].capitalize()}\n\n"
                f"Хорошего дня! 😊"
            )
            # отправка сообщения пользователю
            await bot.send_message(user.user_id, message)
            logger.info(f"Отправлен прогноз погоды для пользователя {user.user_id}")

            # небольшая задержка, чтобы избежать слишком частых запросов к API
            await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Ошибка при отправке прогноза погоды пользователю {user.user_id}: {e}")

async def send_weekly_analysis(bot: Bot):
    """Отправляет еженедельный анализ погоды всем пользователям"""
    logger.info("Запуск рассылки еженедельного анализа погоды")

    async with async_session() as session:
        stmt = select(User).where(User.is_active.is_(True))
        result = await session.execute(stmt)
        users = result.scalars().all()

    for user in users:
        try:
            # получение анализа погоды за неделю
            analysis_data = await WeatherAnalytics.get_weekly_analysis(user.id)

            if not analysis_data:
                logger.warning(f"Не удалось получить еженедельный анализ погоды для пользователя {user.user_id}")
                continue

            # формирование сообщения с аналитикой погоды
            start_date = analysis_data["period"]["start"].strftime("%d.%m")
            end_date = analysis_data["period"]["end"].strftime("%d.%m")

            message = f"📊 Еженедельный анализ погоды за период {start_date} - {end_date} для города {analysis_data['city']}:\n\n"

            # Добавляем информацию о тенденциях
            if analysis_data["trends"]:
                message += "Тенденции за неделю:\n"
                message += f"🌡️ Температура: {analysis_data['trends']['temperature']['description']} "
                message += f"({analysis_data['trends']['temperature']['value']:.1f}°C)\n"
                message += f"💧 Влажность: {analysis_data['trends']['humidity']['description']} "
                message += f"({analysis_data['trends']['humidity']['value']:.1f}%)\n"
                message += f"🌬️ Ветер: {analysis_data['trends']['wind']['description']} "
                message += f"({analysis_data['trends']['wind']['value']:.1f} м/с)\n\n"

            # Добавляем прогноз на следующую неделю
            if analysis_data["next_week_forecast"]:
                message += "🔮 Прогноз на следующую неделю (если тенденция сохранится):\n"
                message += f"🌡️ Температура: {analysis_data['next_week_forecast']['temperature']:.1f}°C\n"
                message += f"💧 Влажность: {analysis_data['next_week_forecast']['humidity']:.1f}%\n"
                message += f"🌬️ Ветер: {analysis_data['next_week_forecast']['wind']:.1f} м/с\n\n"

            # Отправляем сообщение пользователю
            await bot.send_message(user.user_id, message)
            logger.info(f"Отправлен еженедельный анализ погоды пользователю {user.user_id}")

            # Добавляем небольшую задержку, чтобы не перегружать API
            await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Ошибка при отправке еженедельного анализа пользователю {user.user_id}: {e}")


def schedule_jobs(scheduler: AsyncIOScheduler, bot: Bot):
    """Настройка и запуск планировщика заданий.
    Отправка ежедневного прогноза погоды в 8 утра и отправка еженедельного анализа погоды в воскресенье в 12:00
    """
    # Отправка ежедневного прогноза погоды в 8 утра
    scheduler.add_job(
        send_daily_weather,
        trigger=CronTrigger(hour=8, minute=0),
        kwargs={"bot": bot},
        id="daily_weather",
        replace_existing=True
        )
    logger.info("Настроена задача на отправку ежедневного прогноза погоды в 8:00")

    # Отправка еженедельного анализа погоды в воскресенье в 12:00
    scheduler.add_job(
        send_weekly_analysis,
        trigger=CronTrigger(day_of_week="sun", hour=12, minute=0),
        kwargs={"bot": bot},
        id="weekly_analysis",
        replace_existing=True
    )

    logger.info("Настроена задача на отправку еженедельного анализа погоды в 12:00 на воскресенье")

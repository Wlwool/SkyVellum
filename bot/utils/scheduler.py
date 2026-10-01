import logging
import asyncio
from sqlalchemy.future import select
from aiogram import Bot
from typing import Any
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
        stmt = select(User).where(User.is_active.is_(True))
        result = await session.execute(stmt)
        users = result.scalars().all()

    for user in users:
        try:
            # получение прогноза погоды для города пользователя
            weather_data: dict[str, Any] | None = await weather_api.get_current_weather(
                user.city  # type: ignore[arg-type]
            )

            if not weather_data:
                logger.warning(
                    f"Не удалось получить погоду для "
                    f"пользователя {user.user_id}, город: {user.city}"
                )
                continue

            # сохранение данных о погоде для еженедельного анализа
            await WeatherAnalytics.save_weather_data_for_week_analysis(
                user.id,
                weather_data,  # type: ignore[arg-type]
            )

            # формирование сообщения с прогнозом погоды
            message = (
                f"☀️ Доброе утро! Вот прогноз погоды на утро "
                f"для города {weather_data['city']}:\n\n"
                f"🌡️ Температура: {weather_data['temperature']:.1f}°C "
                f"(ощущается как {weather_data['feels_like']:.1f}°C)\n"
                f"💧 Влажность: {weather_data['humidity']}%\n"
                f"🌬️ Ветер: {weather_data['wind_speed']} м/с\n"
                f"🔍 {weather_data['description'].capitalize()}\n\n"
                f"Хорошего дня! 😊"
            )
            # отправка сообщения пользователю
            await bot.send_message(user.user_id, message)  # type: ignore[arg-type]
            logger.info(f"Отправлен прогноз погоды для пользователя {user.user_id}")

            # небольшая задержка, чтобы избежать слишком частых запросов к API
            await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(
                f"Ошибка при отправке прогноза погоды пользователю {user.user_id}: {e}"
            )


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
            # (прошлая неделя и прогноз на следующие 5 дней)
            analysis_data = await WeatherAnalytics.get_weekly_analysis_with_forecast(
                user.id,
                weather_api,  # type: ignore[arg-type]
            )

            if not analysis_data:
                logger.warning(
                    f"Не удалось получить еженедельный анализ погоды "
                    f"для пользователя {user.user_id}"
                )
                continue

            message = (
                f"📊 Еженедельный анализ погоды для города {analysis_data['city']}:\n\n"
            )

            # Добавляем информацию о тенденциях
            if analysis_data["past_week"]:
                past = analysis_data["past_week"]
                start_date = past["period"]["start"].strftime("%d.%m")
                end_date = past["period"]["end"].strftime("%d.%m")
                message += f"Прошедшая неделя ({start_date} - {end_date}):\n\n"

                if past["trends"]:
                    message += "📈 Тенденции за неделю:\n"
                    message += (
                        f"🌡️ Температура: "
                        f"{past['trends']['temperature']['description']} "
                    )
                    message += f"({past['trends']['temperature']['value']:.1f}°C)\n"
                    message += (
                        f"💧 Влажность: {past['trends']['humidity']['description']} "
                    )
                    message += f"({past['trends']['humidity']['value']:.1f}%)\n"
                    message += f"🌬️ Ветер: {past['trends']['wind']['description']} "
                    message += f"({past['trends']['wind']['value']:.1f} м/с)\n\n"
            else:
                message += f"Прошедшая неделя: недостаточно данных для анализа.\n\n"

            # Добавляем прогноз на следующую неделю
            if analysis_data["next_week_forecast"]:
                forecast = analysis_data["next_week_forecast"]
                message += f"Прогноз на следующую неделю:\n\n"

                for day_forecast in forecast["daily_forecasts"]:
                    date_str = (
                        day_forecast["date"].strftime("%d.%m")
                        if hasattr(day_forecast["date"], "strftime")
                        else str(day_forecast["date"])
                    )
                    message += (
                        f"📅 {date_str}: {day_forecast['avg_temp']:+.1f}°C "
                        f"(от {day_forecast['min_temp']:+.1f}°C до "
                        f"{day_forecast['max_temp']:+.1f}°C)\n"
                        f"   💧 {day_forecast['avg_humidity']:.0f}% | "
                        f"🌬️ {day_forecast['avg_wind']:.1f} м/с | "
                        f"{day_forecast['description'].capitalize()}\n\n"
                    )
                summary = forecast["summary"]
                message += (
                    "🔮 Прогноз на следующую неделю (если тенденция сохранится):\n"
                )
                message += (
                    f"🌡️ Температура: {summary['avg_temp']:+.1f}°C "
                    f"(от {summary['min_temp']:+.1f}°C "
                    f"до {summary['max_temp']:+.1f}°C)\n"
                )
                message += f"💧 Влажность: {summary['avg_humidity']:.0f}%\n"
                message += f"🌬️ Ветер: {summary['avg_wind']:.1f} м/с\n"

            # Отправляем сообщение пользователю
            await bot.send_message(user.user_id, message)  # type: ignore[arg-type]
            logger.info(
                f"Отправлен еженедельный анализ погоды пользователю {user.user_id}"
            )

            # Небольшую задержка, чтобы не перегружать API
            await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(
                f"Ошибка при отправке еженедельного анализа "
                f"пользователю {user.user_id}: {e}"
            )


def schedule_jobs(scheduler: AsyncIOScheduler, bot: Bot):
    """Настройка и запуск планировщика заданий.
    Отправка ежедневного прогноза погоды в 8 утра и отправка
    еженедельного анализа погоды в воскресенье в 12:00
    """
    # Отправка ежедневного прогноза погоды в 8 утра
    scheduler.add_job(
        send_daily_weather,
        trigger=CronTrigger(hour=8, minute=0),
        kwargs={"bot": bot},
        id="daily_weather",
        replace_existing=True,
    )
    logger.info("Настроена задача на отправку ежедневного прогноза погоды в 8:00")

    # Отправка еженедельного анализа погоды в воскресенье в 12:00
    scheduler.add_job(
        send_weekly_analysis,
        trigger=CronTrigger(day_of_week="sun", hour=12, minute=0),
        kwargs={"bot": bot},
        id="weekly_analysis",
        replace_existing=True,
    )

    logger.info(
        "Настроена задача на отправку еженедельного анализа погоды "
        "в 12:00 на воскресенье"
    )

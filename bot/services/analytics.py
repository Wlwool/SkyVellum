import logging
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import func, and_
from sqlalchemy.future import select
from bot.database.models import WeatherData, User
from bot.database.database import async_session

logger = logging.getLogger(__name__)


class WeatherAnalytics:
    @staticmethod
    async def get_weekly_analysis(user_id):
        """Получение еженедельного анализа погоды для пользователя из база данных"""
        try:
            async with async_session() as session:
                # данные о пользователе
                user_stmt = select(User).where(User.id == user_id)
                user_result = await session.execute(user_stmt)
                user = user_result.scalar_one_or_none()

                if not user:
                    logger.error(f"Пользователь {user_id} не найден.")
                    return None

                # определение временного диапазона за последние 7 дней
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)

                # получение погодных данных за неделю
                stmt = select(WeatherData).where(
                    and_(
                        WeatherData.user_id == user.id,
                        WeatherData.date >= start_date,
                        WeatherData.date <= end_date
                    )
                ).order_by(WeatherData.date)

                result = await session.execute(stmt)
                weather_data = result.scalars().all()

                if not weather_data:
                    logger.warning(f"Данные погоды за неделю для пользователя {user_id} не найдены.")
                    return None

                return WeatherAnalytics._analyze_weekly_data(weather_data, user.city)
        except Exception as e:
            logger.error(f"Ошибка при получении анализа погоды: {e}")
            return None

    @staticmethod
    def _analyze_weekly_data(weather_data: dict[str, Any], city: str) -> dict[str, Any] | None:
        """Анализ погодных данных за неделю и формирование отчета:
        Группирует данные по дням.
        Вычисляет средние, минимальные и максимальные значения для каждого дня.
        Определяет тенденции изменения температуры, влажности и ветра.
        Формирует прогноз на следующую неделю на основе тенденций.
        Возвращает структурированный отчет.
        """
        try:
            daily_data = {}  # Словарь для хранения данных о погоде по дням недели

            # группировка данных о погоде по дням
            for data in weather_data:
                day = data.date.date()
                if day not in daily_data:
                    daily_data[day] = []
                daily_data[day].append(data)

            # анализ данных по дням недели
            daily_analysis = []
            for day, data_list in daily_data.items():
                avg_temp = sum(data.temperature for data in data_list) / len(data_list)
                min_temp = min(data.temperature for data in data_list)
                max_temp = max(data.temperature for data in data_list)
                avg_humidity = sum(data.humidity for data in data_list) / len(data_list)
                avg_wind = sum(data.wind_speed for data in data_list) / len(data_list)

                daily_analysis.append({
                    "date": day,
                    "avg_temp": avg_temp,
                    "min_temp": min_temp,
                    "max_temp": max_temp,
                    "avg_humidity": avg_humidity,
                    "avg_wind": avg_wind
                })

            # сортировка данных по дате
            daily_analysis.sort(key=lambda x: x["date"])

            # определение тенденций
            if len(daily_analysis) >= 2:
                first_day = daily_analysis[0]
                last_day = daily_analysis[-1]

                temp_trend = last_day["avg_temp"] - first_day["avg_temp"]
                humidity_trend = last_day["avg_humidity"] - first_day["avg_humidity"]
                wind_trend = last_day["avg_wind"] - first_day["avg_wind"]

                trends = {
                    "temperature": {
                        "value": temp_trend,
                        "description": "повышение" if temp_trend > 0 else "понижение" if temp_trend < 0 else "стабильность"
                    },
                    "humidity": {
                        "value": humidity_trend,
                        "description": "повышение" if humidity_trend > 0 else "понижение" if humidity_trend < 0 else "стабильность"
                    },
                    "wind": {
                        "value": wind_trend,
                        "description": "усиление" if wind_trend > 0 else "ослабление" if wind_trend < 0 else "стабильность"
                    }
                }

                # Прогноз на следующую неделю
                next_week_forecast = {
                    "temperature": last_day["avg_temp"] + temp_trend,
                    "humidity": last_day["avg_humidity"] + humidity_trend,
                    "wind": last_day["avg_wind"] + wind_trend
                }
            else:
                trends = None
                next_week_forecast = None

            return {
                "city": city,
                "period": {
                    "start": daily_analysis[0]["date"] if daily_analysis else None,
                    "end": daily_analysis[-1]["date"] if daily_analysis else None
                },
                "daily_analysis": daily_analysis,
                "trends": trends,
                "next_week_forecast": next_week_forecast

            }
        except Exception as e:
            logger.error(f"Ошибка при анализе данных погоды: {e}")
            return None

    @staticmethod
    async def save_weather_data_for_week_analysis(user_id: int, weather_data: dict[str, Any]):
        """
        Сохраняет данные о погоде для еженедельного анализа.
        :param user_id: ID пользователя
        :param weather_data: данные о погоде - температуре, влажности, ветре и т.д.
        :return:
        """
        try:
            # Создаем запись о погоде для анализа
            async with async_session() as session:
                # Создаем новую запись WeatherData
                new_weather_data = WeatherData(
                    user_id=user_id,
                    temperature=weather_data["temperature"],
                    feels_like=weather_data["feels_like"],
                    pressure=weather_data["pressure"],
                    humidity=weather_data["humidity"],
                    wind_speed=weather_data["wind_speed"],
                    description=weather_data["description"]
                )
                session.add(new_weather_data)
                await session.commit()
                logger.info(f"Сохранена погодная информация для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении погодных данных для пользователя {user_id}: {e}")

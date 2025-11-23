import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from sqlalchemy import and_
from sqlalchemy.future import select
from bot.database.models import WeatherData, User
from bot.database.database import async_session

logger = logging.getLogger(__name__)


class WeatherAnalytics:
    @staticmethod
    async def get_weekly_analysis(user_id):
        """Получение еженедельного анализа погоды для пользователя из база данных.
        Используется для ручного запроса пользователя по команде
        """
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
    def _analyze_weekly_data(weather_data: list, city: str) -> Optional[dict[str, Any]]:
        """Анализ погодных данных за неделю и формирование отчета:
        Группирует данные по дням.
        Вычисляет средние, минимальные и максимальные значения для каждого дня.
        Определяет тенденции изменения температуры, влажности и ветра.
        Формирует прогноз на следующую неделю на основе тенденций.
        Возвращает структурированный отчет.
        """
        try:
            if not weather_data or len(weather_data) < 2:
                logger.warning(
                    f"Недостаточно данных для анализа: {len(weather_data) if weather_data else 0} записей")
                return None

            daily_data = {}  # Словарь для хранения данных о погоде по дням

            # Группировка данных о погоде по дням
            for data in weather_data:
                day = data.date.date() if hasattr(data.date, 'date') else data.date
                if day not in daily_data:
                    daily_data[day] = []
                daily_data[day].append(data)

            # Анализ данных по дням недели (усредняем все записи за день)
            daily_analysis = []
            for day, data_list in daily_data.items():
                avg_temp = sum(d.temperature for d in data_list) / len(data_list)
                min_temp = min(d.temperature for d in data_list)
                max_temp = max(d.temperature for d in data_list)
                avg_humidity = sum(d.humidity for d in data_list) / len(data_list)
                avg_wind = sum(d.wind_speed for d in data_list) / len(data_list)

                daily_analysis.append({
                    "date": day,
                    "avg_temp": round(avg_temp, 1),
                    "min_temp": round(min_temp, 1),
                    "max_temp": round(max_temp, 1),
                    "avg_humidity": round(avg_humidity, 1),
                    "avg_wind": round(avg_wind, 1)
                })

            # Сортировка данных по дате
            daily_analysis.sort(key=lambda x: x["date"])

            # Определение тенденций
            if len(daily_analysis) >= 2:
                days_for_trend = min(2, len(daily_analysis) // 2)

                first_days = daily_analysis[:days_for_trend]
                last_days = daily_analysis[-days_for_trend:]

                first_avg_temp = sum(d["avg_temp"] for d in first_days) / len(first_days)
                last_avg_temp = sum(d["avg_temp"] for d in last_days) / len(last_days)

                first_avg_humidity = sum(d["avg_humidity"] for d in first_days) / len(
                    first_days)
                last_avg_humidity = sum(d["avg_humidity"] for d in last_days) / len(
                    last_days)

                first_avg_wind = sum(d["avg_wind"] for d in first_days) / len(first_days)
                last_avg_wind = sum(d["avg_wind"] for d in last_days) / len(last_days)

                temp_trend = last_avg_temp - first_avg_temp
                humidity_trend = last_avg_humidity - first_avg_humidity
                wind_trend = last_avg_wind - first_avg_wind

                trends = {
                    "temperature": {
                        "value": round(temp_trend, 1),
                        "description": WeatherAnalytics._get_trend_description(temp_trend,
                                                                               "temperature")
                    },
                    "humidity": {
                        "value": round(humidity_trend, 1),
                        "description": WeatherAnalytics._get_trend_description(
                            humidity_trend, "humidity")
                    },
                    "wind": {
                        "value": round(wind_trend, 1),
                        "description": WeatherAnalytics._get_trend_description(wind_trend,
                                                                               "wind")
                    }
                }
            else:
                trends = None

            return {
                "city": city,
                "period": {
                    "start": daily_analysis[0]["date"] if daily_analysis else None,
                    "end": daily_analysis[-1]["date"] if daily_analysis else None
                },
                "daily_analysis": daily_analysis,
                "trends": trends
            }

        except Exception as e:
            logger.error(f"Ошибка при анализе данных погоды: {e}", exc_info=True)
            return None

    @staticmethod
    async def get_weekly_analysis_with_forecast(user_id: int, weather_api) -> Optional[dict[str, Any]]:
        """
        Метод воскресной рассылки, который получает анализ погоды за последнюю неделю и прогноз на следующие 5 дней из апи.
        :param user_id: IF пользователя, внутренний ID из таблицы User
        :param weather_api: Экземпляр WeatherAPI для получения прогноза
        :return: словарь с анализом прошлой недели и прогнозом на следующую неделю
        """
        try:
            async with async_session() as session:
                user_stmt = select(User).where(User.id == user_id)
                user_result = await session.execute(user_stmt)
                user = user_result.scalar_one_or_none()

                if not user:
                    logger.error(f"Пользователь c ID {user_id} не найден.")
                    return None

                past_week_analysis = await WeatherAnalytics.get_weekly_analysis(user_id)  # анализ прошлой недели из бд
                forecast_data = await weather_api.get_forecast(user.city, days=5)

                if not forecast_data:
                    logger.error(f"Ошибка при получении прогноза погоды для {user.city}")
                    # Если нет прогноза, вернем хотя бы анализ прошлой недели
                    return {
                        "city": user.city,
                        "past_week": past_week_analysis,
                        "next_week_forecast": None
                    }
                # обработка прогноза
                forecast_analysis = WeatherAnalytics._analyze_forecast(forecast_data)
                return {
                    "city": user.city,
                    "past_week": past_week_analysis,
                    "next_week_forecast": forecast_analysis
                }
        except Exception as e:
            logger.error(f"Ошибка при получении анализа погоды с прогнозом: {e}")
            return None

    @staticmethod
    def _analyze_forecast(forecast_data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """
        Анализирует прогноз на 5 дней из апи.
        :param forecast_data: данные прогноза из weather_api.get_forecast()
        :return: словарь с прогнозом и средними значениями
        """
        try:
            if not forecast_data or "forecasts" not in forecast_data:
                logger.error("Некорректная структура данных прогноза")
                return None

            forecasts = forecast_data["forecasts"][:5]  # Берем только 5 дней

            if not forecasts:
                logger.warning("Прогноз не содержит данных")
                return None

            # Подробный прогноз по дням
            daily_forecasts = []
            for forecast in forecasts:
                daily_forecasts.append({
                    "date": forecast["date"],
                    "avg_temp": round(forecast["avg_temp"], 1),
                    "min_temp": round(forecast["min_temp"], 1),
                    "max_temp": round(forecast["max_temp"], 1),
                    "avg_humidity": round(forecast["avg_humidity"], 1),
                    "avg_wind": round(forecast["avg_wind"], 1),
                    "description": forecast["description"]
                })

            # Среднее за весь прогнозируемый период
            avg_temp = sum(f["avg_temp"] for f in daily_forecasts) / len(daily_forecasts)
            avg_humidity = sum(f["avg_humidity"] for f in daily_forecasts) / len(
                daily_forecasts)
            avg_wind = sum(f["avg_wind"] for f in daily_forecasts) / len(daily_forecasts)

            overall_min_temp = min(f["min_temp"] for f in daily_forecasts)
            overall_max_temp = max(f["max_temp"] for f in daily_forecasts)

            return {
                "daily_forecasts": daily_forecasts,
                "summary": {
                    "avg_temp": round(avg_temp, 1),
                    "min_temp": round(overall_min_temp, 1),
                    "max_temp": round(overall_max_temp, 1),
                    "avg_humidity": round(avg_humidity, 1),
                    "avg_wind": round(avg_wind, 1)
                },
                "days_count": len(daily_forecasts)
            }

        except Exception as e:
            logger.error(f"Ошибка при анализе прогноза: {e}", exc_info=True)
            return None

    @staticmethod
    def _get_trend_description(value: float, metric_type: str) -> str:
        """Возвращает текстовое описание тенденции"""
        # порог незначительного изменения (меньше 1 градуса, %, м/с)
        if abs(value) < 1.0:
            return "стабильность"
        if metric_type == "temperature":
            return "повышение" if value > 0 else "понижение"
        elif metric_type == "humidity":
            return "повышение" if value > 0 else "понижение"
        elif metric_type == "wind":
            return "усиление" if value > 0 else "ослабление"
        return "изменение"


    @staticmethod
    async def save_weather_data_for_week_analysis(user_id: int, weather_data: dict[str, Any]):
        """
        Сохраняет данные о погоде для еженедельного анализа.
        :param user_id: ID пользователя
        :param weather_data: данные о погоде - температуре, влажности, ветре и т.д.
        :return:
        """
        try:
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

import logging
from datetime import UTC, datetime
from typing import Any

import aiohttp

from bot.config.config import Config

logger = logging.getLogger(__name__)
config = Config()

MIN_READINGS_PER_DAY = 4


class WeatherAPI:
    def __init__(self):
        self.api_key = config.WEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5"

    async def _get_json(
        self, url: str, params: dict[str, Any], what: str
    ) -> dict[str, Any] | None:
        """GET-запрос к OpenWeather. Возвращает JSON ответа или None при сбое.
        what - что запрашивали, для текста в логах."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    error_data = await response.json()
                    logger.error(f"Ошибка при получении данных о {what}: {error_data}")
                    return None
            except Exception as e:
                logger.error(f"Ошибка при получении данных о {what}: {e}")
                return None

    async def get_current_weather(self, city: str) -> dict[str, Any] | None:
        """Получает информацию о текущей погоде по названию города"""
        params = {"q": city, "appid": self.api_key, "units": "metric", "lang": "ru"}
        data = await self._get_json(f"{self.base_url}/weather", params, "погоде")
        return self._parse_weather_data(data) if data else None

    async def get_weather_by_coordinates(
        self, lat: float, lon: float
    ) -> dict[str, Any] | None:
        """Получает информацию о текущей погоде по координатам"""
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": "metric",
            "lang": "ru",
        }
        data = await self._get_json(f"{self.base_url}/weather", params, "погоде")
        return self._parse_weather_data(data) if data else None

    async def get_forecast(self, city, days=7):
        """Получает прогноз погоды на несколько дней"""
        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric",
            "lang": "ru",
            "cnt": days * 8,  # Количество дней * 8 (каждые 3 часа)
        }
        data = await self._get_json(
            f"{self.base_url}/forecast", params, "прогнозе погоды"
        )
        return self._parse_forecast_data(data) if data else None

    def _parse_weather_data(self, data):
        """Обрабатывает данные о погоде и возвращает информацию о текущей погоде"""
        try:
            weather = {
                "city": data["name"],
                "country": data["sys"]["country"],
                "lat": data["coord"]["lat"],
                "lon": data["coord"]["lon"],
                "temperature": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "pressure": data["main"]["pressure"],
                "humidity": data["main"]["humidity"],
                "description": data["weather"][0]["description"],
                "icon": data["weather"][0]["icon"],
                "wind_speed": data["wind"]["speed"],
                "wind_direction": data["wind"]["deg"],
                "clouds": data["clouds"]["all"],
                "timestamp": data["dt"],
                "timezone": data.get("timezone", 0),
                "sunrise": data["sys"]["sunrise"],
                "sunset": data["sys"]["sunset"],
            }
            return weather
        except Exception as e:
            logger.error(f"Ошибка при обработке данных о погоде: {e}")
            return None

    def _parse_forecast_data(self, data):
        """Обрабатывает данные о прогнозе погоды и возвращает
        информацию о прогнозе на несколько дней"""
        try:
            city = data["city"]["name"]
            country = data["city"]["country"]
            tz_offset = data["city"].get("timezone", 0)
            forecasts = []

            # Группируем прогнозы по дням
            day_forecasts = {}
            for item in data["list"]:
                dt = datetime.fromtimestamp(item["dt"] + tz_offset, UTC)
                day = dt.date()

                if day not in day_forecasts:
                    day_forecasts[day] = []

                day_forecasts[day].append(
                    {
                        "time": dt.time(),
                        "temperature": item["main"]["temp"],
                        "feels_like": item["main"]["feels_like"],
                        "pressure": item["main"]["pressure"],
                        "humidity": item["main"]["humidity"],
                        "description": item["weather"][0]["description"],
                        "icon": item["weather"][0]["icon"],
                        "wind_speed": item["wind"]["speed"],
                        "wind_direction": item["wind"]["deg"],
                        "clouds": item["clouds"]["all"],
                    }
                )

            # Создание сводного прогноза на каждый день
            for day, items in day_forecasts.items():
                if len(items) < MIN_READINGS_PER_DAY:
                    continue
                avg_temp = sum(item["temperature"] for item in items) / len(items)
                avg_humidity = sum(item["humidity"] for item in items) / len(items)
                avg_wind = sum(item["wind_speed"] for item in items) / len(items)

                # определение наиболее распространённое значение описания погоды в день
                descriptions = {}
                for item in items:
                    desc = item["description"]
                    if desc in descriptions:
                        descriptions[desc] += 1
                    else:
                        descriptions[desc] = 1

                most_common_desc = max(descriptions.items(), key=lambda x: x[1])[0]

                forecasts.append(
                    {
                        "date": day,
                        "avg_temp": avg_temp,
                        "avg_humidity": avg_humidity,
                        "avg_wind": avg_wind,
                        "description": most_common_desc,
                        "min_temp": min(item["temperature"] for item in items),
                        "max_temp": max(item["temperature"] for item in items),
                        "details": items,
                    }
                )

            return {"city": city, "country": country, "forecasts": forecasts}

        except Exception as e:
            logger.error(f"Ошибка при обработке данных о прогнозе погоды: {e}")
            return None

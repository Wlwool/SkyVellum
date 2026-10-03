import logging
from datetime import UTC, date, datetime
from typing import Any

import aiohttp

from bot.config.config import Config

logger = logging.getLogger(__name__)
config = Config()

MIN_READINGS_PER_DAY = 4
# коды OpenWeather
CITY_NOT_FOUND_STATUSES = (400, 404)
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)


class WeatherAPIError(Exception):
    """Базовая ошибка обращения к OpenWeather."""


class CityNotFoundError(WeatherAPIError):
    """OpenWeather не нашёл город (ответ 404, либо 400 на пустое название)."""


class WeatherServiceError(WeatherAPIError):
    """Сервис недоступен или ответил не так, как ожидалось: сеть, таймаут,
    неверный ключ (401), лимит запросов (429), сбой сервера (5xx),
    неожиданный формат ответа."""


class WeatherAPI:
    def __init__(self) -> None:
        self.api_key = config.WEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self._session: aiohttp.ClientSession | None = None

    def _get_session(self) -> aiohttp.ClientSession:
        """Одна сессия на приложение. Создаётся при первом запросе,
        уже внутри работающего цикла событий."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=REQUEST_TIMEOUT)
        return self._session

    async def close(self) -> None:
        """Закрывает сессию"""
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    async def _get_json(
        self, url: str, params: dict[str, Any], what: str
    ) -> dict[str, Any]:
        """GET-запрос к OpenWeather. Возвращает JSON успешного ответа.
        Бросает CityNotFoundError (400/404) или WeatherServiceError.
        what - что запрашивали, для текста в логах."""
        session = self._get_session()
        try:
            async with session.get(url, params=params) as response:
                status = response.status
                if status == 200:
                    return await response.json()
        except (aiohttp.ClientError, TimeoutError, ValueError) as e:
            logger.error(f"Ошибка при получении данных о {what}: {e!r}")
            raise WeatherServiceError(f"Сбой запроса: {e!r}") from e

        if status in CITY_NOT_FOUND_STATUSES:
            logger.warning(f"OpenWeather не нашёл город (запрос о {what}): {status}")
            raise CityNotFoundError(f"OpenWeather вернул {status}")
        logger.error(f"OpenWeather вернул {status} при запросе о {what}")
        raise WeatherServiceError(f"OpenWeather вернул {status}")

    async def get_current_weather(self, city: str) -> dict[str, Any]:
        """Получает информацию о текущей погоде по названию города.
        Бросает CityNotFoundError или WeatherServiceError."""
        params = {"q": city, "appid": self.api_key, "units": "metric", "lang": "ru"}
        data = await self._get_json(f"{self.base_url}/weather", params, "погоде")
        return self._parse_weather_data(data)

    async def get_forecast(self, city: str, days: int = 7) -> dict[str, Any]:
        """Получает прогноз погоды на несколько дней.
        Бросает CityNotFoundError или WeatherServiceError."""
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
        return self._parse_forecast_data(data)

    def _parse_weather_data(self, data: dict[str, Any]) -> dict[str, Any]:
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
                "wind_direction": data["wind"].get("deg"),
                "clouds": data.get("clouds", {}).get("all"),
                "timestamp": data["dt"],
                "timezone": data.get("timezone", 0),
                "sunrise": data["sys"].get("sunrise"),
                "sunset": data["sys"].get("sunset"),
            }
            return weather
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Ошибка при обработке данных о погоде: {e!r}")
            raise WeatherServiceError("Неожиданный формат ответа о погоде") from e

    def _parse_forecast_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Обрабатывает данные о прогнозе погоды и возвращает
        информацию о прогнозе на несколько дней"""
        try:
            city = data["city"]["name"]
            country = data["city"]["country"]
            tz_offset = data["city"].get("timezone", 0)
            forecasts: list[dict[str, Any]] = []

            # Группируем прогнозы по дням
            day_forecasts: dict[date, list[dict[str, Any]]] = {}
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
                        "wind_direction": item["wind"].get("deg"),
                        "clouds": item.get("clouds", {}).get("all"),
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
                descriptions: dict[str, int] = {}
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

        except (KeyError, IndexError, TypeError, ValueError) as e:
            logger.error(f"Ошибка при обработке данных о прогнозе погоды: {e!r}")
            raise WeatherServiceError("Неожиданный формат ответа о прогнозе") from e


weather_api = WeatherAPI()

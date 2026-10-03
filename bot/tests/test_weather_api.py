import copy
import datetime
from unittest.mock import patch

import aiohttp
import pytest

from bot.services.weather_api import (
    CityNotFoundError,
    WeatherAPI,
    WeatherServiceError,
)

CURRENT_PAYLOAD = {
    "name": "Москва",
    "sys": {"country": "RU", "sunrise": 1790000000, "sunset": 1790040000},
    "coord": {"lat": 55.75, "lon": 37.62},
    "main": {"temp": 12.5, "feels_like": 11.0, "pressure": 1015, "humidity": 70},
    "weather": [{"description": "пасмурно", "icon": "04d"}],
    "wind": {"speed": 3.5, "deg": 200},
    "clouds": {"all": 90},
    "dt": 1790010000,
}

_BASE_TS = 1_790_000_000
_DAY0 = 1_789_948_800


def _forecast_payload(days: int = 3, per_day: int = 8, start: int = _DAY0) -> dict:
    """days суток по per_day записей с шагом 3 часа, начиная с момента start."""
    return {
        "city": {"name": "Москва", "country": "RU"},
        "list": [
            {
                "dt": start + d * 86400 + k * 10800,
                "main": {
                    "temp": 10.0,
                    "feels_like": 9.0,
                    "pressure": 1010,
                    "humidity": 80,
                },
                "weather": [{"description": "дождь", "icon": "10d"}],
                "wind": {"speed": 4.0, "deg": 180},
                "clouds": {"all": 100},
            }
            for d in range(days)
            for k in range(per_day)
        ],
    }


class FakeResponse:
    def __init__(self, status: int, payload: dict | None):
        self.status = status
        self._payload = payload

    async def json(self) -> dict:
        if self._payload is None:
            raise ValueError("тело ответа не JSON")
        return self._payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None


class FakeSession:
    """Подмена aiohttp.ClientSession: запоминает параметры запроса."""

    def __init__(self, response: FakeResponse, error: Exception | None = None):
        self._response = response
        self._error = error
        self.closed = False
        self.calls: list[tuple[str, dict]] = []

    async def close(self) -> None:
        self.closed = True

    def get(self, url: str, params: dict | None = None) -> FakeResponse:
        self.calls.append((url, params or {}))
        if self._error is not None:
            raise self._error
        return self._response


def _fake_http(status: int, payload: dict | None, error: Exception | None = None):
    session = FakeSession(FakeResponse(status, payload), error)
    patcher = patch(
        "bot.services.weather_api.aiohttp.ClientSession", return_value=session
    )
    return patcher, session


async def test_get_current_weather():
    patcher, session = _fake_http(200, CURRENT_PAYLOAD)
    with patcher:
        data = await WeatherAPI().get_current_weather("Москва")

    assert data is not None
    assert data["city"] == "Москва"
    assert data["temperature"] == 12.5
    assert data["humidity"] == 70
    assert data["wind_speed"] == 3.5
    assert data["description"] == "пасмурно"
    _, params = session.calls[0]
    assert params["q"] == "Москва"
    assert params["appid"] == "test-key"


async def test_get_forecast():
    patcher, session = _fake_http(200, _forecast_payload(days=3))
    with patcher:
        data = await WeatherAPI().get_forecast("Москва", days=3)

    assert data is not None
    assert data["city"] == "Москва"
    assert len(data["forecasts"]) == 3
    assert data["forecasts"][0]["avg_temp"] == 10.0
    assert data["forecasts"][0]["description"] == "дождь"
    _, params = session.calls[0]
    assert params["cnt"] == 3 * 8


async def test_invalid_city():
    patcher, _ = _fake_http(404, {"cod": "404", "message": "city not found"})
    with patcher, pytest.raises(CityNotFoundError):
        await WeatherAPI().get_current_weather("InvalidCityName")


async def test_forecast_days_use_city_timezone():
    """День прогноза определяется поясом города, а не сервера."""
    payload = _forecast_payload(days=1, per_day=4, start=_DAY0 + 14 * 3600)
    payload["city"]["timezone"] = 45900  # UTC+12:45

    patcher, _ = _fake_http(200, payload)
    with patcher:
        data = await WeatherAPI().get_forecast("Москва", days=1)

    assert data is not None
    assert data["forecasts"][0]["date"] == datetime.date(2026, 9, 22)


async def test_forecast_skips_partial_days():
    """Дни, где записей меньше половины суток, в прогноз не попадают."""
    payload = _forecast_payload(days=4)
    payload["list"] = payload["list"][6:-5]
    patcher, _ = _fake_http(200, payload)
    with patcher:
        data = await WeatherAPI().get_forecast("Москва", days=4)

    assert data is not None
    assert [f["date"] for f in data["forecasts"]] == [
        datetime.date(2026, 9, 22),
        datetime.date(2026, 9, 23),
    ]


async def test_forecast_invalid_city():
    patcher, _ = _fake_http(404, {"cod": "404", "message": "city not found"})
    with patcher, pytest.raises(CityNotFoundError):
        await WeatherAPI().get_forecast("InvalidCityName")


@pytest.mark.parametrize("status", [401, 429, 500, 503])
async def test_service_errors(status):
    """Неверный ключ, лимит запросов и сбои сервера: не «город не найден»."""
    patcher, _ = _fake_http(status, {"cod": status, "message": "error"})
    with patcher, pytest.raises(WeatherServiceError):
        await WeatherAPI().get_current_weather("Москва")


async def test_error_response_without_json_body():
    """Шлюз вернул не JSON: это сбой сервиса, а не падение с ValueError."""
    patcher, _ = _fake_http(502, None)
    with patcher, pytest.raises(WeatherServiceError):
        await WeatherAPI().get_current_weather("Москва")


@pytest.mark.parametrize(
    "error", [aiohttp.ClientConnectionError("нет сети"), TimeoutError()]
)
async def test_network_error(error):
    patcher, _ = _fake_http(200, {}, error=error)
    with patcher, pytest.raises(WeatherServiceError):
        await WeatherAPI().get_forecast("Москва")


async def test_unexpected_payload_format():
    """Ответ 200, но без нужных полей: сбой сервиса, а не «город не найден»."""
    patcher, _ = _fake_http(200, {"name": "Москва"})
    with patcher, pytest.raises(WeatherServiceError):
        await WeatherAPI().get_current_weather("Москва")


async def test_empty_city_is_not_found():
    """Пустое название: OpenWeather отвечает 400 Nothing to geocode"""
    patcher, _ = _fake_http(400, {"cod": "400", "message": "Nothing to geocode"})
    with patcher, pytest.raises(CityNotFoundError):
        await WeatherAPI().get_current_weather("")


async def test_current_weather_without_sunrise_and_sunset():
    """В полярный день или ночь восхода и заката в ответе может не быть."""
    payload = copy.deepcopy(CURRENT_PAYLOAD)
    del payload["sys"]["sunrise"]
    del payload["sys"]["sunset"]
    patcher, _ = _fake_http(200, payload)
    with patcher:
        data = await WeatherAPI().get_current_weather("Мурманск")

    assert data["sunrise"] is None
    assert data["sunset"] is None
    assert data["temperature"] == 12.5


async def test_current_weather_without_wind_direction_and_clouds():
    """Направление ветра и облачность нам не нужны: их отсутствие не сбой."""
    payload = copy.deepcopy(CURRENT_PAYLOAD)
    del payload["wind"]["deg"]
    del payload["clouds"]
    patcher, _ = _fake_http(200, payload)
    with patcher:
        data = await WeatherAPI().get_current_weather("Москва")

    assert data["wind_direction"] is None
    assert data["clouds"] is None
    assert data["wind_speed"] == 3.5


async def test_forecast_without_wind_direction_and_clouds():
    """То же для прогноза: нужные для расчёта поля на месте, остальных нет."""
    payload = _forecast_payload(days=1)
    for item in payload["list"]:
        del item["wind"]["deg"]
        del item["clouds"]
    patcher, _ = _fake_http(200, payload)
    with patcher:
        data = await WeatherAPI().get_forecast("Москва", days=1)

    assert len(data["forecasts"]) == 1


async def test_session_is_reused_between_requests():
    """Одна сессия на все запросы (в ней пул соединений), а не новая на каждый."""
    patcher, _ = _fake_http(200, CURRENT_PAYLOAD)
    api = WeatherAPI()
    with patcher as session_factory:
        await api.get_current_weather("Москва")
        await api.get_current_weather("Москва")

    assert session_factory.call_count == 1


async def test_session_has_request_timeout():
    """Таймаут задан явно: по умолчанию у aiohttp он 5 минут."""
    patcher, _ = _fake_http(200, CURRENT_PAYLOAD)
    with patcher as session_factory:
        await WeatherAPI().get_current_weather("Москва")

    assert session_factory.call_args.kwargs["timeout"].total == 10


async def test_close_closes_session():
    patcher, session = _fake_http(200, CURRENT_PAYLOAD)
    api = WeatherAPI()
    with patcher:
        await api.get_current_weather("Москва")
        await api.close()

    assert session.closed is True


async def test_close_without_requests_is_safe():
    """Бот остановили, не сделав ни одного запроса: close() не должен падать."""
    await WeatherAPI().close()


def test_modules_share_one_weather_api():
    """Везде один экземпляр WeatherAPI, значит одна сессия на приложение."""
    from bot.handlers import registration, weather
    from bot.services.weather_api import weather_api
    from bot.utils import scheduler

    assert scheduler.weather_api is weather_api
    assert weather.weather_api is weather_api
    assert registration.weather_api is weather_api

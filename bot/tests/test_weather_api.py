import datetime
from unittest.mock import patch

from bot.services.weather_api import WeatherAPI

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

_BASE_TS = 1_790_000_000  # шаг 86400 с гарантирует разные даты в любом поясе


def _forecast_payload(days: int = 3) -> dict:
    return {
        "city": {"name": "Москва", "country": "RU"},
        "list": [
            {
                "dt": _BASE_TS + i * 86400,
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
            for i in range(days)
        ],
    }


class FakeResponse:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self._payload = payload

    async def json(self) -> dict:
        return self._payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None


class FakeSession:
    """Подмена aiohttp.ClientSession: запоминает параметры запроса."""

    def __init__(self, response: FakeResponse):
        self._response = response
        self.calls: list[tuple[str, dict]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None

    def get(self, url: str, params: dict | None = None) -> FakeResponse:
        self.calls.append((url, params or {}))
        return self._response


def _fake_http(status: int, payload: dict):
    session = FakeSession(FakeResponse(status, payload))
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
    with patcher:
        data = await WeatherAPI().get_current_weather("InvalidCityName")

    assert data is None


async def test_forecast_days_use_city_timezone():
    """День прогноза определяется поясом города, а не сервера."""
    payload = _forecast_payload(days=1)
    payload["city"]["timezone"] = 45900  # UTC+12:45

    patcher, _ = _fake_http(200, payload)
    with patcher:
        data = await WeatherAPI().get_forecast("Москва", days=1)

    assert data is not None
    assert data["forecasts"][0]["date"] == datetime.date(2026, 9, 22)

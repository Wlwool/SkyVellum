import pytest
import asyncio
from bot.services.weather_api import WeatherAPI


@pytest.mark.asyncio
async def test_get_current_weather():
    """Тест получения погоды"""
    weather_api = WeatherAPI()
    weather_data = await weather_api.get_current_weather("Москва")

    assert weather_data is not None
    assert "city" in weather_data
    assert weather_data["city"] == "Москва"
    assert "temperature" in weather_data
    assert "humidity" in weather_data
    assert "wind_speed" in weather_data
    assert "description" in weather_data

@pytest.mark.asyncio
async def test_get_forecast():
    """Тест получения прогноза погоды"""
    weather_api = WeatherAPI()
    forecast_data = await weather_api.get_forecast("Moscow", days=3)

    assert forecast_data is not None
    assert "city" in forecast_data
    assert forecast_data["city"] == "Moscow"
    assert "forecast" in forecast_data
    assert len(forecast_data["forecast"]) >= 3

@pytest.mark.asyncio
async def test_invalid_city():
    """Тест получения погоды с неверным названием города"""
    weather_api = WeatherAPI()
    weather_data = await weather_api.get_current_weather("InvalidCityName")

    assert weather_data is None

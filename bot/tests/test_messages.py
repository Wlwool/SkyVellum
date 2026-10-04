from bot.services.messages import (
    format_daily_weather,
    format_trends,
    format_weekly_broadcast,
)

TRENDS = {
    "temperature": {"description": "повышение", "value": 5.0},
    "humidity": {"description": "понижение", "value": -5.0},
    "wind": {"description": "ослабление", "value": -2.5},
}


def test_format_trends_uses_given_title():
    """Общий блок тенденций: заголовок задаёт вызывающий код."""
    text = format_trends(TRENDS, "Заголовок:")

    assert text.startswith("Заголовок:\n")
    assert "Температура: повышение (5.0°C)" in text
    assert "Влажность: понижение (-5.0%)" in text
    assert "Ветер: ослабление (-2.5 м/с)" in text
    assert text.endswith("\n\n")


def test_format_daily_weather():
    """Утреннее сообщение: одна цифра после запятой, описание с заглавной."""
    weather = {
        "city": "Москва",
        "temperature": 10.0,
        "feels_like": 8.0,
        "humidity": 70,
        "wind_speed": 3.0,
        "description": "ясно",
    }

    text = format_daily_weather(weather)

    assert "для города Москва:" in text
    assert "Температура: 10.0°C (ощущается как 8.0°C)" in text
    assert "Ясно" in text


def test_format_weekly_broadcast_without_data():
    """Нет ни недели, ни прогноза: заголовок и пояснение, без секции прогноза."""
    analysis = {"city": "Москва", "past_week": None, "next_week_forecast": None}

    text = format_weekly_broadcast(analysis)

    assert "для города Москва:" in text
    assert "недостаточно данных для анализа" in text
    assert "Прогноз на следующую неделю" not in text

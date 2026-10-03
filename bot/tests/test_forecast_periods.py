import datetime

import pytest

from bot.handlers.weather import select_forecast_days

TODAY = datetime.date(2026, 10, 3)


def _days(*numbers: int) -> list[dict]:
    """Прогноз из дней октября 2026: нужны только даты."""
    return [{"date": datetime.date(2026, 10, n)} for n in numbers]


def test_tomorrow_returns_only_next_day():
    result = select_forecast_days(_days(3, 4, 5, 6, 7), "tomorrow", TODAY)
    assert result == _days(4)


def test_tomorrow_missing_returns_empty():
    """Завтрашнего дня в прогнозе нет (в нём меньше 4 записей): пусто."""
    assert select_forecast_days(_days(3, 5, 6), "tomorrow", TODAY) == []


def test_three_days_returns_first_three():
    result = select_forecast_days(_days(3, 4, 5, 6, 7), "3days", TODAY)
    assert result == _days(3, 4, 5)


def test_five_days_returns_first_five():
    result = select_forecast_days(_days(3, 4, 5, 6, 7, 8), "5days", TODAY)
    assert result == _days(3, 4, 5, 6, 7)


def test_unknown_period_raises():
    with pytest.raises(ValueError):
        select_forecast_days(_days(3, 4), "month", TODAY)

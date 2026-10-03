from datetime import UTC, datetime

from bot.utils.timeutils import format_local_time, is_local_time_due

# 1790000000 = 21.09.2026 14:13:20 UTC


def test_moscow_offset():
    assert format_local_time(1790000000, 10800) == "17:13:20"


def test_utc_offset():
    assert format_local_time(1790000000, 0) == "14:13:20"


def test_offset_with_minutes():
    """UTC+12:45 (45900 с): сдвиг не кратен часу и переходит на следующие сутки."""
    assert format_local_time(1790000000, 45900) == "02:58:20"


# 21.09.2026 - понедельник, 27.09.2026 - воскресенье


def test_due_at_local_eight():
    """05:00 UTC при смещении Москвы (+3 ч) - это 08:00 по местному времени."""
    now = datetime(2026, 9, 21, 5, 0, tzinfo=UTC)
    assert is_local_time_due(now, 10800, hour=8) is True


def test_window_boundaries():
    """Окно 15 минут: 07:59 рано, 08:14 ещё можно, 08:15 уже поздно."""
    assert not is_local_time_due(datetime(2026, 9, 21, 4, 59, tzinfo=UTC), 10800, 8)
    assert is_local_time_due(datetime(2026, 9, 21, 5, 14, tzinfo=UTC), 10800, 8)
    assert not is_local_time_due(datetime(2026, 9, 21, 5, 15, tzinfo=UTC), 10800, 8)


def test_zero_offset_user_gets_eight_utc():
    """Смещение 0 - это 08:00 UTC, а не 08:00 по Москве."""
    assert not is_local_time_due(datetime(2026, 9, 21, 5, 0, tzinfo=UTC), 0, 8)
    assert is_local_time_due(datetime(2026, 9, 21, 8, 0, tzinfo=UTC), 0, 8)


def test_offset_with_half_hour():
    """UTC+5:30 (19800 с): 08:00 по местному - это 02:30 UTC."""
    assert is_local_time_due(datetime(2026, 9, 21, 2, 30, tzinfo=UTC), 19800, 8)
    assert not is_local_time_due(datetime(2026, 9, 21, 2, 0, tzinfo=UTC), 19800, 8)


def test_negative_offset():
    """UTC-4 (-14400 с): 08:00 по местному - это 12:00 UTC."""
    assert is_local_time_due(datetime(2026, 9, 21, 12, 0, tzinfo=UTC), -14400, 8)


def test_weekday_uses_local_date():
    """19:15 UTC в воскресенье при UTC+12:45 - уже понедельник 08:00 по местному."""
    now = datetime(2026, 9, 20, 19, 15, tzinfo=UTC)
    assert is_local_time_due(now, 45900, 8, weekday=0) is True
    assert is_local_time_due(now, 45900, 8, weekday=6) is False


def test_weekly_sunday_noon():
    """Воскресная рассылка: воскресенье 12:00 по Москве, в понедельник - нет."""
    sunday = datetime(2026, 9, 27, 9, 0, tzinfo=UTC)
    monday = datetime(2026, 9, 28, 9, 0, tzinfo=UTC)
    assert is_local_time_due(sunday, 10800, 12, weekday=6) is True
    assert is_local_time_due(monday, 10800, 12, weekday=6) is False

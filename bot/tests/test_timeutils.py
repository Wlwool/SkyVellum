from bot.utils.timeutils import format_local_time

# 1790000000 = 21.09.2026 14:13:20 UTC


def test_moscow_offset():
    assert format_local_time(1790000000, 10800) == "17:13:20"


def test_utc_offset():
    assert format_local_time(1790000000, 0) == "14:13:20"


def test_offset_with_minutes():
    """UTC+12:45 (45900 с): сдвиг не кратен часу и переходит на следующие сутки."""
    assert format_local_time(1790000000, 45900) == "02:58:20"

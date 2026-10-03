from datetime import UTC, datetime, timedelta


def format_local_time(timestamp: int, tz_offset: int) -> str:
    """Unix-время (UTC) -> 'ЧЧ:ММ:СС' по местному времени города.
    tz_offset - смещение города от UTC в секундах (поле timezone из OpenWeather)
    """
    return datetime.fromtimestamp(timestamp + tz_offset, UTC).strftime("%H:%M:%S")


def is_local_time_due(
    now_utc: datetime,
    tz_offset: int,
    hour: int,
    weekday: int | None = None,
    window_minutes: int = 15,
) -> bool:
    """Попадает ли местное время города в окно [hour:00, hour:00 + window).

    now_utc - текущее время в UTC (с tzinfo).
    tz_offset - смещение города от UTC в секундах.
    weekday - если задан, местный день недели должен совпасть
    (понедельник = 0, воскресенье = 6). День считается по местной дате.
    Планировщик срабатывает каждые window_minutes минут, поэтому каждый
    пользователь попадает в окно ровно один раз в сутки.
    """
    local = now_utc + timedelta(seconds=tz_offset)
    if weekday is not None and local.weekday() != weekday:
        return False
    start = local.replace(hour=hour, minute=0, second=0, microsecond=0)
    return start <= local < start + timedelta(minutes=window_minutes)

from datetime import UTC, datetime


def format_local_time(timestamp: int, tz_offset: int) -> str:
    """Unix-время (UTC) -> 'ЧЧ:ММ:СС' по местному времени города.
    tz_offset - смещение города от UTC в секундах (поле timezone из OpenWeather)
    """
    return datetime.fromtimestamp(timestamp + tz_offset, UTC).strftime("%H:%M:%S")

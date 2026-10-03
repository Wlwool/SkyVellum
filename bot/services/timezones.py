import asyncio
import logging

from bot.database.database import engine
from bot.services.users import get_active_users, update_timezone_offset
from bot.services.weather_api import WeatherAPI, WeatherAPIError

logger = logging.getLogger(__name__)


async def refresh_timezone_offsets(api: WeatherAPI) -> tuple[int, int]:
    """Подтягивает смещение пояса у всех активных пользователей из OpenWeather.
    Нужно один раз после перехода на рассылку по местному времени: у старых
    пользователей в БД стоит 0. Возвращает (получено, не удалось получить).
    """
    updated = failed = 0
    for user in await get_active_users():
        try:
            weather = await api.get_current_weather(user.city)
        except WeatherAPIError as e:
            logger.warning(
                f"Нет данных о погоде для пользователя {user.user_id}, "
                f"город: {user.city}: {e}"
            )
            failed += 1
            continue
        await update_timezone_offset(user.id, weather["timezone"])
        updated += 1
    return updated, failed


async def _main() -> None:
    try:
        updated, failed = await refresh_timezone_offsets(WeatherAPI())
    finally:
        await engine.dispose()
    print(f"Смещение получено: {updated}, не удалось: {failed}")


if __name__ == "__main__":
    asyncio.run(_main())

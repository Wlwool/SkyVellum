import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids() -> list[int]:
    """Читает ADMIN_IDS из окружения: "1,2,3" -> [1, 2, 3]."""
    admin_ids = os.environ.get("ADMIN_IDS", "")
    return [int(admin_id) for admin_id in admin_ids.split(",") if admin_id]


@dataclass
class Config:
    """
    Класс конфигурации бота, хранящий в себе настройки переменных окружения.
    Переменные читаются в момент создания Config(), а не при импорте модуля.
    Атрибуты:
        BOT_TOKEN (str): Токен Telegram-бота. Обязательно.
        WEATHER_API_KEY (str): API-ключ для сервиса погоды.
        DB_URL (str): URL подключения к БД (асинхронный драйвер).
            По умолчанию SQLite в папке database.
        ADMIN_IDS (list[int]): Список ID администраторов бота - необязательно.
    """

    BOT_TOKEN: str = field(default_factory=lambda: os.environ.get("BOT_TOKEN", ""))
    WEATHER_API_KEY: str = field(
        default_factory=lambda: os.environ.get("WEATHER_API_KEY", "")
    )
    DB_URL: str = field(
        default_factory=lambda: os.environ.get(
            "DB_URL", "sqlite+aiosqlite:///database/weather_bot.db"
        )
    )
    ADMIN_IDS: list[int] = field(default_factory=_parse_admin_ids)

    def validate(self) -> None:
        """Проверяет обязательные переменные окружения.
        Вызывается один раз при старте бота. Собирает все отсутствующие
        переменные сразу, чтобы не перезапускать бота по одной.
        """
        required = {
            "BOT_TOKEN": self.BOT_TOKEN,
            "WEATHER_API_KEY": self.WEATHER_API_KEY,
        }
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            raise ValueError(
                "Не заданы обязательные переменные окружения: "
                f"{', '.join(missing)}. Заполните их в .env (см. .env-example)."
            )

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """
    Класс конфигурации бота, хранящий в себе настройки переменных окружения.
    Атрибуты:
        BOT_TOKEN (str): Токен Telegram-бота. Обязательно.
        WEATHER_API_KEY (str): API-ключ для сервиса погоды.
        DB_URL (str): URL подключения к БД. По умолчанию SQLite в папке database.
        ADMIN_IDS (list[int]): Список ID администраторов бота - необязательно.
    """
    BOT_TOKEN: str = os.environ.get("BOT_TOKEN")
    WEATHER_API_KEY: str = os.environ.get("WEATHER_API_KEY")
    DB_URL: str = os.environ.get("DB_URL", "sqlite:///database/weather_bot.db")
    ADMIN_IDS: list = None

    def __post_init__(self):
        """Пост-инициализация: парсит ADMIN_IDS из строки в список целых чисел."""
        admin_ids = os.environ.get("ADMIN_IDS", "")
        # Преобразует каждый элемент в число если элемент не пустой
        self.ADMIN_IDS = [int(admin_id) for admin_id in admin_ids.split(",") if admin_id] if admin_ids else []

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    BOT_TOKEN: str = os.environ.get("BOT_TOKEN")
    WEATHER_API_KEY: str = os.environ.get("WEATHER_API_KEY")
    DB_URL: str = os.environ.get("DB_URL", "sqlite:///database/weather_bot.db")
    ADMIN_IDS: list = None

    def __post_init__(self):
        admin_ids = os.environ.get("ADMIN_IDS", "")
        # Преобразует каждый элемент в число если элемент не пустой
        self.ADMIN_IDS = [int(admin_id) for admin_id in admin_ids.split(",") if admin_id] if admin_ids else []

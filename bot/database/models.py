from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from bot.database.database import Base


class User(Base):
    """
    Модель для хранения данных о пользователях бота.
    Атрибуты:
        id (int): Уникальный идентификатор записи
        user_id (int): Уникальный идентификатор пользователя в Telegram
        username (str): Никнейм пользователя (опционально)
        city (str): Название города для прогноза погоды (обязательно)
        latitude (float): Географическая широта (для точного прогноза)
        longitude (float): Географическая долгота (для точного прогноза)
        timezone_offset (int): смещение часового пояса города от UTC в секундах
        is_active (bool): Флаг активности пользователя (для мягкого удаления)
        registered_at (datetime): Дата и время регистрации (автоматически)

    Связи:
        weather_data (list[WeatherData]): История запросов погоды пользователя
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None]
    first_name: Mapped[str | None]
    last_name: Mapped[str | None]
    city: Mapped[str]
    latitude: Mapped[float | None]
    longitude: Mapped[float | None]
    timezone_offset: Mapped[int] = mapped_column(default=0, server_default="0")
    is_active: Mapped[bool | None] = mapped_column(default=True)
    registered_at: Mapped[datetime | None] = mapped_column(server_default=func.now())

    weather_data: Mapped[list["WeatherData"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, user_id={self.user_id}, city={self.city})>"


class WeatherData(Base):
    """
    Модель для хранения данных о погоде.
    Атрибуты:
        id (int): Уникальный идентификатор записи
        user_id (int): Идентификатор пользователя, которому принадлежит данная запись
        temperature (float): Температура в градусах Цельсия
        feels_like (float): Ощущаемая температура в градусах Цельсия
        pressure (int): Атмосферное давление в миллиметрах ртутного столба
        humidity (int): Влажность воздуха в процентах
        wind_speed (float): Скорость ветра в м/с
        description (str): Текстовое описание погодных условий
        date (datetime): Время записи данных (автоматически)

    Связи:
        user (User): Связанный пользователь, выполнивший запрос
    """

    __tablename__ = "weather_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    temperature: Mapped[float | None]
    feels_like: Mapped[float | None]
    pressure: Mapped[int | None]
    humidity: Mapped[int | None]
    wind_speed: Mapped[float | None]
    description: Mapped[str | None]
    date: Mapped[datetime | None] = mapped_column(default=func.now())

    # связь с таблицей пользователей
    user: Mapped["User"] = relationship(back_populates="weather_data")

    def __repr__(self) -> str:
        return (
            f"<WeatherData(id={self.id}, user_id={self.user_id}, "
            f"temperature={self.temperature}, date={self.date})>"
        )

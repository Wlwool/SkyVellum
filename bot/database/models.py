from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    city = Column(String, nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    is_active = Column(Boolean, default=True)
    registered_at = Column(DateTime, server_default=func.now())

    weather_data = relationship("WeatherData", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, user_id={self.user_id}, city={self.city})>"


class WeatherData(Base):
    __tablename__ = "weather_data"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    temperature = Column(Float)
    feels_like = Column(Float)
    pressure = Column(Integer)
    humidity = Column(Integer)
    wind_speed = Column(Float)
    description = Column(String)
    date = Column(DateTime, default=func.now())

    # связь с таблицей пользователей
    user = relationship("User", back_populates="weather_data")

    def __repr__(self):
        return f"<WeatherData(id={self.id}, user_id={self.user_id}, temperature={self.temperature}, date={self.date})>"

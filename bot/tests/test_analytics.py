import pytest
import datetime
from bot.database.models import User, WeatherData
from bot.database.database import async_session
from bot.services.analytics import WeatherAnalytics


@pytest.mark.asyncio
async def test_weekly_analysis():
    """Тест еженедельного анализа погоды."""
    # создание тестового пользователя
    async with async_session() as session:
        test_user = User(user_id=999999, username="test_user",
                         first_name="TestName", last_name="TestLastName",
                         city="TestCity")
        session.add(test_user)
        await session.commit()

        # получение id пользователя
        user_id = test_user.id

        # создание тестовых данных о погоде за неделю
        now = datetime.datetime.now()
        for i in range(7):
            date = now - datetime.timedelta(days=i)
            weather_data = WeatherData(
                user_id=user_id,
                temperature=20.0 - i,  # Температура понижается
                feels_like=19.0 - i,
                pressure=1010 + i,
                humidity=60 + i,  # Влажность повышается
                wind_speed=5.0 + i * 0.5,  # Ветер усиливается
                description="Облачно",
                date=date
            )
            session.add(weather_data)

        await session.commit()

        # получение анализа погоды
        analysis_data = await WeatherAnalytics.get_weekly_analysis(999999)

        # проверка результатов анализа
        assert analysis_data is not None
        assert "city" in analysis_data
        assert analysis_data["city"] == "TestCity"
        assert "trends" in analysis_data
        assert "temperature" in analysis_data["trends"]
        assert "humidity" in analysis_data["trends"]
        assert "wind" in analysis_data["trends"]

        # проверка тенденций температуры
        assert analysis_data["trends"]["temperature"]["description"] == "понижение"
        assert analysis_data["trends"]["humidity"]["description"] == "повышение"
        assert analysis_data["trends"]["wind"]["description"] == "усиление"

        # удаление тестовых данных
        await session.delete(test_user)
        await session.commit()




import datetime

from bot.database.database import async_session
from bot.database.models import WeatherData
from bot.services.analytics import WeatherAnalytics


async def test_weekly_analysis(make_user):
    """Тенденции за неделю: теплеет, влажность падает, ветер слабеет."""
    user_id = await make_user(user_id=999999, city="TestCity")

    now = datetime.datetime.now()
    async with async_session() as session:
        for i in range(7):
            # i=6 — самая старая запись, i=0 — самая свежая
            session.add(
                WeatherData(
                    user_id=user_id,
                    temperature=20.0 - i,
                    feels_like=19.0 - i,
                    pressure=1010 + i,
                    humidity=60 + i,
                    wind_speed=5.0 + i * 0.5,
                    description="Облачно",
                    date=now - datetime.timedelta(days=i),
                )
            )
        await session.commit()

    # get_weekly_analysis ждёт внутренний User.id, а не Telegram-ID
    analysis = await WeatherAnalytics.get_weekly_analysis(user_id)

    assert analysis is not None
    assert analysis["city"] == "TestCity"
    trends = analysis["trends"]
    assert trends["temperature"]["description"] == "повышение"
    assert trends["humidity"]["description"] == "понижение"
    assert trends["wind"]["description"] == "ослабление"


async def test_weekly_analysis_unknown_user(db):
    """Несуществующий пользователь: None, без исключения."""
    assert await WeatherAnalytics.get_weekly_analysis(424242) is None

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from bot.utils.scheduler import send_weekly_analysis
from bot.database.models import User


@pytest.mark.asyncio
async def test_send_weekly_analysis_success():
    """
    Тест успешной отправки еженедельного анализа
    """
    # Мокаем бота
    bot_mock = AsyncMock()

    # Подготовка моковых данных пользователей
    user1 = MagicMock(spec=User)
    user1.user_id = 123456
    user1.id = 1
    user1.is_active = True

    # Мокаем сессию и результат запроса к БД
    with patch("bot.utils.scheduler.async_session") as mock_session:
        mock_exec = AsyncMock()
        mock_exec.scalars.return_value.all.return_value = [user1]
        mock_session().__aenter__.return_value.execute = mock_exec

        # Мокаем WeatherAnalytics и API
        with patch("bot.utils.scheduler.WeatherAnalytics") as mock_analytics, \
                patch("bot.utils.scheduler.weather_api") as mock_weather_api:

            mock_analytics.get_weekly_analysis_with_forecast.return_value = {
                "city": "Москва",
                "past_week": {
                    "period": {
                        "start": MagicMock(strftime=MagicMock(return_value="01.04")),
                        "end": MagicMock(strftime=MagicMock(return_value="07.04"))
                    },
                    "trends": {
                        "temperature": {"description": "повысилась", "value": 15.5},
                        "humidity": {"description": "снизилась", "value": 60.0},
                        "wind": {"description": "усилился", "value": 3.2}
                    }
                },
                "next_week_forecast": [
                    {
                        "date": MagicMock(strftime=MagicMock(return_value="08.04")),
                        "avg_temp": 16.0,
                        "min_temp": 12.0,
                        "max_temp": 20.0,
                        "avg_humidity": 55.0,
                        "avg_wind": 2.8,
                        "description": "переменная облачность"
                    }
                ],
                "summary": {
                    "avg_temp": 16.5,
                    "min_temp": 11.0,
                    "max_temp": 21.0,
                    "avg_humidity": 58.0,
                    "avg_wind": 3.0
                }
            }

            # Запуск функции
            await send_weekly_analysis(bot=bot_mock)

            # Проверки
            bot_mock.send_message.assert_awaited_once()
            call_args = bot_mock.send_message.call_args
            assert call_args[0][0] == 123456  # user_id
            assert "Москва" in call_args[1]["text"]
            assert "01.04 - 07.04" in call_args[1]["text"]
            assert "Прогноз на следующую неделю" in call_args[1]["text"]


@pytest.mark.asyncio
async def test_send_weekly_analysis_no_data():
    """
    Тест поведения при отсутствии данных аналитики
    """
    bot_mock = AsyncMock()

    user1 = MagicMock(spec=User)
    user1.user_id = 123456
    user1.id = 1
    user1.is_active = True

    with patch("bot.utils.scheduler.async_session") as mock_session:
        mock_exec = AsyncMock()
        mock_exec.scalars.return_value.all.return_value = [user1]
        mock_session().__aenter__.return_value.execute = mock_exec

        with patch("bot.utils.scheduler.WeatherAnalytics") as mock_analytics:
            mock_analytics.get_weekly_analysis_with_forecast.return_value = None

            await send_weekly_analysis(bot=bot_mock)

            # Проверяем, что сообщение НЕ было отправлено
            bot_mock.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_send_weekly_analysis_user_inactive():
    """
    Тест: неактивные пользователи не получают рассылку
    """
    bot_mock = AsyncMock()

    user1 = MagicMock(spec=User)
    user1.user_id = 123456
    user1.is_active = False  # неактивный

    with patch("bot.utils.scheduler.async_session") as mock_session:
        mock_exec = AsyncMock()
        mock_exec.scalars.return_value.all.return_value = [user1]
        mock_session().__aenter__.return_value.execute = mock_exec

        await send_weekly_analysis(bot=bot_mock)

        bot_mock.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_send_weekly_analysis_exception_handling():
    """
    Тест: обработка ошибок при отправке сообщения
    """
    bot_mock = AsyncMock()
    bot_mock.send_message.side_effect = Exception("API Error")

    user1 = MagicMock(spec=User)
    user1.user_id = 123456
    user1.id = 1
    user1.is_active = True

    with patch("bot.utils.scheduler.async_session") as mock_session, \
            patch("bot.utils.scheduler.WeatherAnalytics") as mock_analytics, \
            patch("bot.utils.scheduler.logger.error") as mock_log_error:

        mock_exec = AsyncMock()
        mock_exec.scalars.return_value.all.return_value = [user1]
        mock_session().__aenter__.return_value.execute = mock_exec

        mock_analytics.get_weekly_analysis_with_forecast.return_value = {
            "city": "Москва",
            "past_week": {
                "period": {"start": MagicMock(strftime=MagicMock(return_value="01.04")), "end": MagicMock(strftime=MagicMock(return_value="07.04"))},
                "trends": {"temperature": {"description": "повысилась", "value": 15.5}}
            },
            "next_week_forecast": []
        }

        await send_weekly_analysis(bot=bot_mock)

        # Проверка, что ошибка была залогирована
        mock_log_error.assert_called()
        assert "API Error" in str(mock_log_error.call_args)

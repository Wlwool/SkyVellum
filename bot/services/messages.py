from typing import Any

from bot.utils.timeutils import format_local_time


def _local_time_or_no_data(timestamp: int | None, tz_offset: int) -> str:
    """Местное время для вывода. Нет значения (полярный день/ночь) - нет данных"""
    if timestamp is None:
        return "нет данных"
    return format_local_time(timestamp, tz_offset)


def format_current_weather(weather_data: dict[str, Any], timestamp: int) -> str:
    """Текст Погоды сейчас. timestamp - момент в UTC для строки - обновлено."""
    tz_offset = weather_data["timezone"]
    sunrise_time = _local_time_or_no_data(weather_data["sunrise"], tz_offset)
    sunset_time = _local_time_or_no_data(weather_data["sunset"], tz_offset)
    formatted_time = format_local_time(timestamp, tz_offset)
    return (
        f"Погода в городе {weather_data['city']} ({weather_data['country']}):\n\n"
        f"🌡️ Температура: {weather_data['temperature']:.1f}°C "
        f"(ощущается как {weather_data['feels_like']:.1f}°C)\n"
        f"💧 Влажность: {weather_data['humidity']}%\n"
        f"🌬️ Ветер: {weather_data['wind_speed']} м/с\n"
        f"🔍 {weather_data['description'].capitalize()}\n\n"
        f"🌅 Восход солнца: {sunrise_time}\n"
        f"🌇 Закат солнца: {sunset_time}\n\n"
        f"🕒 Данные обновлены: {formatted_time}\n*** Хорошего дня! ***"
    )


def format_forecast(
    forecast_data: dict[str, Any], forecasts: list[dict[str, Any]], title: str
) -> str:
    """Текст прогноза: заголовок и по блоку на каждый день из forecasts."""
    text = (
        f"{title} для города {forecast_data['city']} ({forecast_data['country']}):\n\n"
    )
    for forecast in forecasts:
        date_str = forecast["date"].strftime("%d.%m")
        text += (
            f"📅 {date_str}:\n"
            f"🌡️ Температура: {forecast['avg_temp']:.1f}°C "
            f"(от {forecast['min_temp']:.1f}°C до {forecast['max_temp']:.1f}°C)\n"
            f"💧 Влажность: {forecast['avg_humidity']:.0f}%\n"
            f"🌬️ Ветер: {forecast['avg_wind']:.1f} м/с\n"
            f"🔍 {forecast['description'].capitalize()}\n\n"
        )
    return text


def format_daily_weather(weather_data: dict[str, Any]) -> str:
    """Текст утренней рассылки."""
    return (
        f"☀️ Доброе утро! Вот прогноз погоды на утро "
        f"для города {weather_data['city']}:\n\n"
        f"🌡️ Температура: {weather_data['temperature']:.1f}°C "
        f"(ощущается как {weather_data['feels_like']:.1f}°C)\n"
        f"💧 Влажность: {weather_data['humidity']}%\n"
        f"🌬️ Ветер: {weather_data['wind_speed']} м/с\n"
        f"🔍 {weather_data['description'].capitalize()}\n\n"
        f"Хорошего дня! 😊"
    )


def format_trends(trends: dict[str, Any], title: str) -> str:
    """Блок тенденций за неделю. title - заголовок блока (с эмодзи)."""
    return (
        f"{title}\n"
        f"🌡️ Температура: {trends['temperature']['description']} "
        f"({trends['temperature']['value']:.1f}°C)\n"
        f"💧 Влажность: {trends['humidity']['description']} "
        f"({trends['humidity']['value']:.1f}%)\n"
        f"🌬️ Ветер: {trends['wind']['description']} "
        f"({trends['wind']['value']:.1f} м/с)\n\n"
    )


def format_weekly_analysis(analysis_data: dict[str, Any]) -> str:
    """Текст кнопки Еженедельный анализ: прошлая неделя по дням из БД."""
    start_date = analysis_data["period"]["start"].strftime("%d.%m")
    end_date = analysis_data["period"]["end"].strftime("%d.%m")

    text = (
        f"Анализ погоды за период {start_date} - {end_date} "
        f"для города {analysis_data['city']}:\n\n"
    )

    if analysis_data["trends"]:
        text += format_trends(analysis_data["trends"], "📊 Тенденции за неделю:")

    text += "📅 Данные по дням:\n"
    for day_data in analysis_data["daily_analysis"]:
        date_str = day_data["date"].strftime("%d.%m")
        text += (
            f"- {date_str}: {day_data['avg_temp']:.1f}°C, "
            f"влажность {day_data['avg_humidity']:.0f}%, "
            f"ветер {day_data['avg_wind']:.1f} м/с\n"
        )
    return text


def format_weekly_broadcast(analysis_data: dict[str, Any]) -> str:
    """Текст воскресной рассылки: прошлая неделя и прогноз на следующую."""
    message = f"📊 Еженедельный анализ погоды для города {analysis_data['city']}:\n\n"

    if analysis_data["past_week"]:
        past = analysis_data["past_week"]
        start_date = past["period"]["start"].strftime("%d.%m")
        end_date = past["period"]["end"].strftime("%d.%m")
        message += f"Прошедшая неделя ({start_date} - {end_date}):\n\n"

        if past["trends"]:
            message += format_trends(past["trends"], "📈 Тенденции за неделю:")
    else:
        message += "Прошедшая неделя: недостаточно данных для анализа.\n\n"

    if analysis_data["next_week_forecast"]:
        forecast = analysis_data["next_week_forecast"]
        message += "Прогноз на следующую неделю:\n\n"

        for day_forecast in forecast["daily_forecasts"]:
            date_str = (
                day_forecast["date"].strftime("%d.%m")
                if hasattr(day_forecast["date"], "strftime")
                else str(day_forecast["date"])
            )
            message += (
                f"📅 {date_str}: {day_forecast['avg_temp']:+.1f}°C "
                f"(от {day_forecast['min_temp']:+.1f}°C до "
                f"{day_forecast['max_temp']:+.1f}°C)\n"
                f"   💧 {day_forecast['avg_humidity']:.0f}% | "
                f"🌬️ {day_forecast['avg_wind']:.1f} м/с | "
                f"{day_forecast['description'].capitalize()}\n\n"
            )
        summary = forecast["summary"]
        message += "🔮 Прогноз на следующую неделю (если тенденция сохранится):\n"
        message += (
            f"🌡️ Температура: {summary['avg_temp']:+.1f}°C "
            f"(от {summary['min_temp']:+.1f}°C "
            f"до {summary['max_temp']:+.1f}°C)\n"
        )
        message += f"💧 Влажность: {summary['avg_humidity']:.0f}%\n"
        message += f"🌬️ Ветер: {summary['avg_wind']:.1f} м/с\n"

    return message

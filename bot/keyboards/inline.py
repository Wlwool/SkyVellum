from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_forecast_keyboard() -> InlineKeyboardMarkup:
    """Возвращает инлайн-клавиатуру для получения прогноза погоды"""
    keyboard = [
        [
            InlineKeyboardButton(text="Сегодня", callback_data="forecast:today"),
            InlineKeyboardButton(text="Завтра", callback_data="forecast:tomorrow")
        ],
        [
            InlineKeyboardButton(text="3 дня", callback_data="forecast:3days"),
            InlineKeyboardButton(text="5 дней", callback_data="forecast:5days")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_cities_keyboard(cities: list) -> InlineKeyboardMarkup:
    """Возвращает инлайн-клавиатуру для выбора города"""
    keyboard = []

    for city in cities:
        keyboard.append([InlineKeyboardButton(text=city, callback_data=f"city:{city}")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

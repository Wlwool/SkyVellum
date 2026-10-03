from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_forecast_keyboard() -> InlineKeyboardMarkup:
    """Возвращает инлайн-клавиатуру для выбора периода прогноза погоды"""
    keyboard = [
        [
            InlineKeyboardButton(text="Сейчас", callback_data="forecast:now"),
            InlineKeyboardButton(text="Завтра", callback_data="forecast:tomorrow"),
        ],
        [
            InlineKeyboardButton(text="3 дня", callback_data="forecast:3days"),
            InlineKeyboardButton(text="5 дней", callback_data="forecast:5days"),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_start_keyboard(is_registered: bool = False) -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру основного меню для начала работы с ботом"""
    keyboard = []

    if is_registered:
        keyboard.append([KeyboardButton(text="Погода сейчас")])
        keyboard.append([KeyboardButton(text="Погода на 5 дней")])
        keyboard.append([KeyboardButton(text="Еженедельный анализ")])
        keyboard.append([KeyboardButton(text="Изменить город")])
    else:
        keyboard.append([KeyboardButton(text="Зарегистрироваться")])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_weather_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру для выбора варианта работы с погодой"""
    keyboard = [
        [KeyboardButton(text="Погода сейчас")],
        [KeyboardButton(text="Погода на 5 дней")],
        [KeyboardButton(text="Еженедельный анализ")],
        [KeyboardButton(text="Изменить город")]
    ]

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

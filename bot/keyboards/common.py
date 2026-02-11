from aiogram.types import ReplyKeyboardMarkup, KeyboardButton



def get_cancel_reply_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Отмена")]
    ], resize_keyboard=True,
    one_time_keyboard=True)
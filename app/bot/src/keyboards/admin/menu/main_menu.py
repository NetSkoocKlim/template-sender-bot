from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.bot.src.keyboards.admin.constants import AdminPanelOptions

def get_admin_panel_menu_kb():
    builder = InlineKeyboardBuilder()

    for option in AdminPanelOptions:
        if option != AdminPanelOptions.back:
            builder.button(
                text=option,
                callback_data=option.name
            )

    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.admin.constants import (
    AdminPanelMailingOptions,
    AdminPanelChosenTemplateOptions
)


def get_admin_panel_mailing_menu_kb():
    builder = InlineKeyboardBuilder()
    for option in AdminPanelMailingOptions:
        builder.button(text=option.value, callback_data=option.name)

    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def get_admin_panel_chosen_template_kb():
    builder = InlineKeyboardBuilder()
    for option in AdminPanelChosenTemplateOptions:
        builder.button(text=option.value, callback_data=option.name)
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)



from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.admin.constants import AdminPanelReceiverOptions


def get_admin_panel_receiver_menu_kb():
    builder = InlineKeyboardBuilder()

    for option in AdminPanelReceiverOptions:
        builder.button(
            text=option.value,
            callback_data=option.name
        )

    builder.adjust(1, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_receivers_list_kb(need_download: bool = False):
    builder = InlineKeyboardBuilder()

    if need_download:
        builder.row(
            InlineKeyboardButton(
                text="Скачать полный список",
                callback_data="download_receivers_list"
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="back_to_receivers_menu"
        )
    )

    return builder.as_markup(resize_keyboard=True)
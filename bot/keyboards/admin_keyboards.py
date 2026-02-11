from enum import StrEnum, auto, Enum
from typing import Sequence, Optional

from aiogram.filters.callback_data import CallbackData
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from database.models import Template


class AdminPanelOptions(StrEnum):
    user_list = "Управление списком пользователей"
    template = "Управление шаблонами"
    statistic = "Просмотр статистики"
    mailing = "Управление рассылкой"
    back = "Вернуться к админ-панели"


def get_admin_panel_menu_kb():
    builder = ReplyKeyboardBuilder()

    for button in AdminPanelOptions:
        if button != AdminPanelOptions.back:
            builder.button(text=button)

    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


class AdminPanelTemplateOptions(StrEnum):
    add_template = "Создать новый шаблон"
    edit_template = "Посмотреть созданные шаблоны"
    back = AdminPanelOptions.back


def get_admin_panel_template_menu_kb():
    builder = ReplyKeyboardBuilder()

    for button in AdminPanelTemplateOptions:
        builder.button(text=button)

    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


class TemplateEditAction(StrEnum):
    view = auto()
    choose = auto()
    edit_name = auto()
    edit_description = auto()
    delete = auto()
    to_templates_edit_list = auto()

    from_ = auto()

action_to_text = {
    TemplateEditAction.edit_name: "Изменить название",
    TemplateEditAction.edit_description: "Изменить описание",
    TemplateEditAction.delete: "Удалить шаблон",
    TemplateEditAction.to_templates_edit_list: "Назад",
    TemplateEditAction.choose: "Выбрать для рассылки"
}


class TemplateEditData(CallbackData, prefix="edit_template"):
    action: TemplateEditAction
    id: int
    index: int | None = None
    creator_id: int

    is_chosen: bool = False

def get_templates_inline_kb(templates: Sequence[Template], chosen_template_id: int | None = None):
    builder = InlineKeyboardBuilder()
    for index, template in enumerate(templates, start=1):
        button_name = f"Шаблон {index}"
        template_is_chosen = False
        if chosen_template_id is not None and int(chosen_template_id) == template.id:
            button_name = " (Выбран ✅)  " + button_name
            template_is_chosen = True
        button_name = button_name + f": {template.name}"

        builder.button(
            text=button_name,
            callback_data=TemplateEditData(action=TemplateEditAction.view, id=template.id, index=index,
                                           creator_id=template.creator_id,
                                           is_chosen=template_is_chosen
                                           ).pack(),
        )

    builder.button(
        text="Назад",
        callback_data="back_to_templates_menu"
    )
    builder.adjust(1)

    return builder.as_markup(resize_keyboard=True)


def get_template_edit_inline_kb(template: Template, template_is_chosen: bool, template_index: int):
    builder = InlineKeyboardBuilder()
    for action in TemplateEditAction:
        if template_is_chosen and action == TemplateEditAction.choose:
            continue
        if (action != TemplateEditAction.view and
            action != TemplateEditAction.from_
        ):
            builder.button(
                text=action_to_text[action],
                callback_data=TemplateEditData(action=action, id=template.id,
                                               index=template_index,
                                               creator_id=template.creator_id,
                                               is_chosen=template_is_chosen).pack(),
            )
    builder.adjust(1,2, 1)
    return builder.as_markup(resize_keyboard=True)



class AdminPanelReceiverOptions(StrEnum):
    view = "Посмотреть список пользователей"
    expand = "Добавить пользователей в список"
    delete = "Удалить пользователей из списка"
    clear = "Полностью очистить список пользователей"


def get_admin_panel_receiver_menu_kb():
    builder = ReplyKeyboardBuilder()
    for button in AdminPanelReceiverOptions:
        builder.button(text=button)

    builder.button(
        text=AdminPanelOptions.back
    )
    builder.adjust(1, 2, 1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

class ReceiverData(CallbackData, prefix="receiver_data"):
    username: str

def get_receivers_list_kb(receivers: str):
    builder = InlineKeyboardBuilder()
    for receiver in receivers.split():
        builder.button(text=receiver,
                       callback_data=ReceiverData(username=receiver).pack())
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="back_to_receivers_menu"
        )
    )
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


class AdminPanelMailingOptions(StrEnum):
    choose_template = "Выбрать шаблон"
    begin_mailing = "Начать рассылку"


def get_admin_panel_mailing_menu_kb():
    builder = ReplyKeyboardBuilder()
    for button in AdminPanelReceiverOptions:
        builder.button(text=button)

    builder.button(
        text=AdminPanelOptions.back
    )
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

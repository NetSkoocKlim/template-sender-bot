from enum import StrEnum, auto, Enum
from typing import Sequence, Optional

from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from database.models import Template


class AdminPanelOptions(StrEnum):
    user_list = "Управление списком пользователей"
    template = "Редактирование шаблонов"
    statistic = "Просмотр статистики"
    dispatch = "Управление рассылкой"


def get_admin_panel_menu_kb():
    builder = ReplyKeyboardBuilder()

    for button in AdminPanelOptions:
        builder.button(text=button)

    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


class AdminPanelTemplateOptions(StrEnum):
    add_template = "Создать новый шаблон"
    edit_template = "Редактировать существующие шаблоны"
    back = "Вернуться к панели администратора"


def get_admin_panel_template_menu_kb():
    builder = ReplyKeyboardBuilder()

    for button in AdminPanelTemplateOptions:
        builder.button(text=button)

    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


class TemplateEditAction(StrEnum):
    view = auto()
    edit_name = auto()
    edit_description = auto()
    delete = auto()
    to_templates_edit_list = auto()

action_to_text = {
    TemplateEditAction.edit_name: "Изменить название",
    TemplateEditAction.edit_description: "Изменить описание",
    TemplateEditAction.delete: "Удалить шаблон",
    TemplateEditAction.to_templates_edit_list: "Назад"
}


class TemplateEditData(CallbackData, prefix="edit_template"):
    action: TemplateEditAction
    id: int
    index: int | None = None
    creator_id: int


def get_templates_inline_kb(templates: Sequence[Template]):
    builder = InlineKeyboardBuilder()
    for index, template in enumerate(templates, start=1):
        builder.button(
            text=f"Шаблон {index}: " + template.name,
            callback_data=TemplateEditData(action=TemplateEditAction.view, id=template.id, index=index,
                                           creator_id=template.creator_id).pack(),
        )
    builder.button(
        text="Назад",
        callback_data="back_to_templates_menu"
    )
    builder.adjust(1)

    return builder.as_markup(resize_keyboard=True)


def get_template_edit_inline_kb(template: Template, template_index: int):
    builder = InlineKeyboardBuilder()
    for action in TemplateEditAction:
        if action != TemplateEditAction.view:
            builder.button(
                text=action_to_text[action],
                callback_data=TemplateEditData(action=action, id=template.id,
                                               index=template_index,
                                               creator_id=template.creator_id).pack(),
            )
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)




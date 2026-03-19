from typing import Sequence
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import Template
from bot.keyboards.admin.constants import AdminPanelTemplateOptions, TemplateEditAction
from bot.keyboards.admin.fabrics import TemplateEditData
from bot.keyboards.admin.builders import add_pagination_footer


def get_admin_panel_template_menu_kb():
    builder = InlineKeyboardBuilder()

    for option in AdminPanelTemplateOptions:
        builder.button(
            text=option.value,
            callback_data=option.name,
        )

    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_templates_inline_kb(
        templates: Sequence[Template],
        forward_anchor: str | None,
        backward_anchor: str | None,
        page_count: int,
        page: int,
        page_size: int = 5
):
    builder = InlineKeyboardBuilder()

    for index, template in enumerate(templates, start=1):
        global_index = (page - 1) * page_size + index
        prefix = " (Выбран ✅)  " if template.is_chosen_for_mailing else ""
        button_name = f"{prefix}Шаблон {global_index}: {template.name}"

        builder.button(
            text=button_name,
            callback_data=TemplateEditData(
                action=TemplateEditAction.view_tmplt,
                id=template.id,
                creator_id=template.creator_id,
                is_chosen=template.is_chosen_for_mailing,
                name=template.name
            ).pack(),
        )

    builder.adjust(1)

    builder = add_pagination_footer(
        builder=builder,
        page=page,
        page_count=page_count,
        model_name="Template",
        forward_anchor=forward_anchor,
        backward_anchor=backward_anchor,
        back_callback="back_to_templates_menu"
    )

    return builder.as_markup(resize_keyboard=True)


def get_template_edit_inline_kb(template: Template):
    builder = InlineKeyboardBuilder()

    for action in TemplateEditAction:
        if action != TemplateEditAction.view_tmplt:
            builder.button(
                text=action.label,
                callback_data=TemplateEditData(
                    action=action,
                    id=template.id,
                    creator_id=template.creator_id,
                    is_chosen=template.is_chosen_for_mailing,
                    name=template.name
                ).pack(),
            )

    builder.adjust(1, 2, 1)
    return builder.as_markup(resize_keyboard=True)
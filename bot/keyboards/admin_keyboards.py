from enum import StrEnum, auto
from typing import Sequence

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import TemplatePaginator
from database.models import Template, Mailing



class AdminPanelOptions(StrEnum):
    user_list = "Управление списком пользователей"
    template = "Управление шаблонами"
    statistic = "Просмотр статистики"
    mailing = "Управление рассылкой"

    back = "Вернуться к админ-панели"


def get_admin_panel_menu_kb():
    builder = InlineKeyboardBuilder()

    for button in AdminPanelOptions:
        if button != AdminPanelOptions.back:
            builder.button(
                text=button,
                callback_data=button
            )

    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


class AdminPanelTemplateOptions(StrEnum):
    add_template = "Создать новый шаблон"
    edit_template = "Посмотреть созданные шаблоны"
    back = AdminPanelOptions.back


def get_admin_panel_template_menu_kb():
    builder = InlineKeyboardBuilder()

    for button in AdminPanelTemplateOptions:
        builder.button(
            text=button,
            callback_data=button,
        )

    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)


class TemplateEditAction(StrEnum):
    view = auto()
    choose = auto()
    name = auto()
    desc = auto()
    delete = auto()
    back = auto()


action_to_text = {
    TemplateEditAction.name: "Изменить название",
    TemplateEditAction.desc: "Изменить описание",
    TemplateEditAction.delete: "Удалить шаблон",
    TemplateEditAction.back: "Назад",
    TemplateEditAction.choose: "Выбрать для рассылки",
}


class TemplateEditData(CallbackData, prefix="edit_tmplt"):
    action: TemplateEditAction
    id: int
    index: int | None = None
    creator_id: int
    name: str

    is_chosen: bool = False



class PaginateButtonData(CallbackData, prefix="pgnt"):
    anchor: str
    forward: bool = True


def get_templates_inline_kb(templates: Sequence[Template],
                            forward_anchor: str | None,
                            backward_anchor: str | None,
                            page_count: int,
                            page: int
                            ) -> InlineKeyboardMarkup:


    builder = InlineKeyboardBuilder()
    page_size = TemplatePaginator.PAGE_SIZE
    for index, template in enumerate(templates, start=1):
        button_name = f"Шаблон {(page - 1) * page_size + index}"
        template_is_chosen = False
        if template.is_chosen_for_mailing:
            button_name = " (Выбран ✅)  " + button_name
            template_is_chosen = True
        button_name = button_name + f": {template.name}"
        builder.button(
            text=button_name,
            callback_data=TemplateEditData(
                action=TemplateEditAction.view,
                id=template.id,
                index=(page - 1) * page_size + index,
                creator_id=template.creator_id,
                is_chosen=template_is_chosen,
                name=template.name
            ).pack(),
        )

    if not backward_anchor:
        backward_button = InlineKeyboardButton(
            text="#",
            callback_data="empty_pagination"
        )
    else:
        backward_button = InlineKeyboardButton(
            text="<",
            callback_data=PaginateButtonData(
                anchor=backward_anchor,
                forward=False
            ).pack(),
        )

    if not forward_anchor:
        forward_button = InlineKeyboardButton(
            text="#",
            callback_data="empty_pagination"
        )
    else:
        forward_button = InlineKeyboardButton(
            text=">",
            callback_data=PaginateButtonData(
                anchor=forward_anchor,
                forward=True
            ).pack()
        )

    builder.adjust(1)

    page_button = InlineKeyboardButton(
        text=f"{page}/{page_count}",
        callback_data="empty_pagination"
    )

    builder.row(backward_button, page_button, forward_button)

    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data="back_to_templates_menu",
        )
    )

    return builder.as_markup(resize_keyboard=True)


def get_template_edit_inline_kb(template: Template,
                                template_index: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for action in TemplateEditAction:
        if action != TemplateEditAction.view:
            builder.button(
                text=action_to_text[action],
                callback_data=TemplateEditData(
                    action=action,
                    id=template.id,
                    index=template_index,
                    creator_id=template.creator_id,
                    is_chosen=template.is_chosen_for_mailing,
                    name=template.name
                ).pack(),
            )
    builder.adjust(1,2, 1)
    return builder.as_markup(resize_keyboard=True)




class AdminPanelReceiverOptions(StrEnum):
    view = "Посмотреть список пользователей"
    expand = "Добавить пользователей"
    delete = "Удалить пользователей"
    clear = "Очистить список пользователей"

    back = AdminPanelOptions.back


def get_admin_panel_receiver_menu_kb():
    builder = InlineKeyboardBuilder()
    for button in AdminPanelReceiverOptions:
        builder.button(text=button,
                       callback_data=button)

    builder.adjust(1, 2, 1)
    return builder.as_markup(resize_keyboard=True)

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
    view_chosen_template = "Посмотреть выбранный шаблон"
    begin_mailing = "Начать рассылку"

    back = AdminPanelOptions.back


def get_admin_panel_mailing_menu_kb():
    builder = InlineKeyboardBuilder()
    for button in AdminPanelMailingOptions:
        builder.button(text=button,
                       callback_data=button)

    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


class AdminPanelChosenTemplateOptions(StrEnum):
    choose_another = "Выбрать другой шаблон"
    back = "Назад к рассылке"


def get_admin_panel_chosen_template_kb():
    builder = InlineKeyboardBuilder()
    for button in AdminPanelChosenTemplateOptions:
        builder.button(text=button,
                       callback_data=button)
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


class AdminPanelStatisticOptions(StrEnum):
    download = "Скачать результат последней рассылки"
    view = "Посмотреть все рассылки"
    back = AdminPanelOptions.back

class DownloadMailingData(CallbackData, prefix="download_data"):
    key: str


def get_admin_panel_statistic_kb(last_mailing_key):
    builder = InlineKeyboardBuilder()
    builder.button(text=AdminPanelStatisticOptions.download,
                   callback_data=DownloadMailingData(
                       key=last_mailing_key
                   ))
    for button in AdminPanelStatisticOptions:
        if button != AdminPanelStatisticOptions.download:
            builder.button(text=button,
                           callback_data=button)
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


class MailingViewData(CallbackData, prefix="view_data"):
     id: int

# async def get_mailings_inline_kb(
#         mailings: Sequence[Mailing],
#         forward_anchor: Anchor,
#         backward_anchor: Anchor,
#         page: int = 1,
#         page_count: int = 1,
# ):
#     builder = InlineKeyboardBuilder()
#     for mailing in mailings:
#         button_name = f"Рассылка от {mailing.created_at.replace(
#             microsecond=0,
#             second=0,
#         )}"
#         builder.button(
#             text=button_name,
#             callback_data=MailingViewData(
#                 id=mailing.id,
#             ).pack(),
#         )
#
#     if forward_anchor.page == page_count + 1:
#         forward_button = InlineKeyboardButton(
#             text="#",
#             callback_data="empty_pagination"
#         )
#     else:
#         forward_button = InlineKeyboardButton(
#             text=">",
#             callback_data=PaginateButtonData(
#                 model="Mailing",
#                 anchor_page=forward_anchor.page,
#                 anchor_value=forward_anchor.value,
#                 page_count=page_count
#             ).pack()
#         )
#
#     if backward_anchor.page == 0:
#         backward_button = InlineKeyboardButton(
#             text="#",
#             callback_data="empty_pagination"
#         )
#     else:
#         backward_button = InlineKeyboardButton(
#             text="<",
#             callback_data=PaginateButtonData(
#                 model="Mailing",
#                 anchor_page=backward_anchor.page,
#                 anchor_value=backward_anchor.value,
#                 page_count=page_count,
#                 direction=0
#             ).pack(),
#         )
#     page_button = InlineKeyboardButton(
#         text=f"{page}/{page_count}",
#         callback_data="empty_pagination"
#     )
#
#     builder.row(backward_button, page_button, forward_button)
#
#     builder.row(
#         InlineKeyboardButton(
#             text="Назад",
#             callback_data="back_to_statistic_menu",
#         )
#     )
#
#     return builder.as_markup(resize_keyboard=True)
from typing import Sequence

from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.src.keyboards.admin.builders import add_pagination_footer
from app.bot.src.keyboards.admin.constants import AdminPanelStatisticOptions, MailingInfoOptions
from app.bot.src.keyboards.admin.fabrics import DownloadMailingData, MailingViewData, MailingTemplateViewData
from shared.src.database.models import Mailing
from shared.src.database.models.mailing import MailingStatus


def get_admin_panel_statistic_menu_kb(mailing):
    builder = InlineKeyboardBuilder()

    if mailing.save_status == MailingStatus.SAVED.value:
        builder.button(
            text=AdminPanelStatisticOptions.download_mlngRes.value,
            callback_data=DownloadMailingData(key=mailing.s3_key).pack()
        )

    for option in AdminPanelStatisticOptions:
        if option != AdminPanelStatisticOptions.download_mlngRes:
            builder.button(text=option.value, callback_data=option.name)

    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_mailings_inline_kb(
        mailings: Sequence[Mailing],
        forward_anchor: str | None,
        backward_anchor: str | None,
        page_count: int,
        page: int,
        page_size: int = 5
):
    builder = InlineKeyboardBuilder()

    for index, mailing in enumerate(mailings, start=1):
        global_index = (page - 1) * page_size + index
        mailing_date = mailing.created_at.strftime('%d.%m.%Y %H:%M:%S')
        button_text = f"Рассылка {global_index}: от {mailing_date}"

        builder.button(
            text=button_text,
            callback_data=MailingViewData(
                id=mailing.id
            ).pack(),
        )

    builder.adjust(1)

    return add_pagination_footer(
        builder=builder,
        page=page,
        page_count=page_count,
        model_name="Mailing",
        forward_anchor=forward_anchor,
        backward_anchor=backward_anchor,
        back_callback="back_to_statistic_menu"
    ).as_markup(resize_keyboard=True)


def get_mailing_info_inline_kb(mailing: Mailing, template_id: int):
    builder = InlineKeyboardBuilder()

    if mailing.save_status == MailingStatus.SAVED.value:
        builder.button(
            text=MailingInfoOptions.download_lst_mlngRes.value,
            callback_data=DownloadMailingData(key=mailing.s3_key).pack()
        )

    builder.button(
        text=MailingInfoOptions.check_template.value,
        callback_data=MailingTemplateViewData(
            id=template_id,
            mailing_id=mailing.id,
            action="view"
        ).pack()
    )
    builder.button(
        text=MailingInfoOptions.back2st_mlngs.value,
        callback_data=MailingInfoOptions.back2st_mlngs.name
    )

    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)



def get_mailing_template_view_kb(mailing_id):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Назад",
        callback_data=MailingViewData(
            id=mailing_id,
        ).pack()
    )

    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)
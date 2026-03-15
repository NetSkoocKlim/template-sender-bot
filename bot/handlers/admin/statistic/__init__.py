import logging
import sqlalchemy
from aiogram import Router, F, html
from aiogram.types import CallbackQuery, BufferedInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.admin.constants import AdminPanelOptions, AdminPanelStatisticOptions, MailingInfoOptions
from bot.keyboards.admin.fabrics import DownloadMailingData, PaginateButtonData, MailingViewData, \
    MailingTemplateViewData
from bot.keyboards.admin.menu import (get_admin_panel_statistic_menu_kb, get_mailings_inline_kb,
                                      get_mailing_info_inline_kb)
from bot.keyboards.admin.menu.statistic import get_mailing_template_view_kb
from bot.lexicon import LEXICON
from database.models import User, Mailing, Template
from database.paginator.anchor_store import get_page_anchor_state
from database.paginator.paginator import MailingPaginator
from services.object_storage_app.app import ObjectStorageApp

router = Router()

logger = logging.getLogger(__name__)


@router.callback_query(F.data == AdminPanelOptions.statistic.name)
@router.callback_query(F.data == "back_to_statistic_menu")
async def statistic_menu_handler(callback: CallbackQuery,
                                 session: AsyncSession,
                                 admin: User):
    last_mailing: Mailing = await Mailing.get_newest(
        session,
        filter_by={
            "admin_id": admin.id,
        }
    )

    if not last_mailing:
        await callback.answer("Вы ещё не совершали рассылку")
        return
    mailing_count = await Mailing.count_total(
        session,
    )
    last_mailing_date = last_mailing.created_at.strftime("%d.%m.%Y %H:%M:%S")

    def create_short_report():
        mailing_unresolved_count = last_mailing.unresolved_count
        mailing_failed_count = last_mailing.delivery_failed_count
        mailing_success_count = last_mailing.total_requested - mailing_unresolved_count - mailing_failed_count

        return ("Результат последней рассылки:\n"
                f"Успешно отправлено: {mailing_success_count}\n"
                f"Юзер не найден: {mailing_unresolved_count}\n"
                f"Не удалось отправить: {mailing_failed_count}\n")

    await callback.answer()
    await callback.message.edit_text(
        text=LEXICON["ADMIN"]["STATISTIC"]["main"].format(mailing_count, last_mailing_date, create_short_report()),
        reply_markup=get_admin_panel_statistic_menu_kb(last_mailing.csv_result_key)
    )


@router.callback_query(DownloadMailingData.filter())
async def handle_download_last_mailing(
        callback: CallbackQuery,
        callback_data: DownloadMailingData,
        s3_storage: ObjectStorageApp
):
    mailing_key = callback_data.key
    data, meta = await s3_storage.download_file(mailing_key)
    filename = meta.get("filename") or f"mailing-{mailing_key}.csv"
    input_file = BufferedInputFile(data, filename=filename)
    await callback.message.answer_document(document=input_file)
    await callback.answer()


async def get_mailings_list(
        message: Message,
        mailing_sender_id: int,
        session: AsyncSession,
        anchor: str | None = None,
        forward: bool = True,
        is_deletion: bool = False,
        is_back: bool = False,
):
    filters = [sqlalchemy.text(f"mailings.admin_id={mailing_sender_id}")]
    mailings, backward_anchor, forward_anchor, current_page, total_pages = await MailingPaginator.get_next_page(
        user_id=mailing_sender_id,
        session=session,
        anchor=anchor,
        filters=filters,
        forward=forward,
        is_deletion=is_deletion,
        is_back=is_back,
    )
    try:
        await message.edit_text(
            LEXICON["ADMIN"]["STATISTIC"]["mailings_list"],
            reply_markup=get_mailings_inline_kb(
                mailings,
                forward_anchor=forward_anchor,
                backward_anchor=backward_anchor,
                page_count=total_pages,
                page=current_page,
                page_size=MailingPaginator.PAGE_SIZE
            )
        )
    except Exception as e:
        logger.exception(e)


@router.callback_query(F.data == AdminPanelStatisticOptions.view_mlngs.name)
async def handle_view_all_mailings_button(
        callback: CallbackQuery,
        admin: User,
        session: AsyncSession,
):
    await callback.answer()
    await get_mailings_list(
        message=callback.message,
        mailing_sender_id=admin.id,
        session=session,
    )


@router.callback_query(PaginateButtonData.filter(F.model == "Mailing"))
async def handle_mailing_pagination(
        callback: CallbackQuery,
        callback_data: PaginateButtonData,
        session: AsyncSession,
        admin: User,
):
    anchor = callback_data.anchor
    forward: bool = callback_data.forward
    await get_mailings_list(
        message=callback.message,
        mailing_sender_id=admin.id,
        session=session,
        anchor=anchor,
        forward=forward,
    )
    await callback.answer()


@router.callback_query(F.data == MailingInfoOptions.back2st_mlngs.name)
async def handle_back_to_mailings(
        callback: CallbackQuery,
        session: AsyncSession,
        admin: User,
):
    anchor, forward, _ = await get_page_anchor_state(
        admin.id
    )
    await callback.answer()
    await get_mailings_list(
        message=callback.message,
        mailing_sender_id=admin.id,
        session=session,
        anchor=anchor,
        forward=forward,
        is_back=True
    )

@router.callback_query(MailingViewData.filter())
async def handle_mailing_view(
        callback: CallbackQuery,
        callback_data: MailingViewData,
        session: AsyncSession,
):
    mailing_id = callback_data.id

    mailing = await Mailing.get(
        session=session,
        primary_key=mailing_id,
    )

    def compute_mailing_info() -> str:
        failed_count = mailing.unresolved_count + mailing.delivery_failed_count
        if failed_count == 0:
            return "Сообщение успешно доставлено всем пользователям"

        mailing_info = (f"Успешно доставлено: {mailing.total_requested - failed_count}/{mailing.total_requested}\n"
                        f"Пользователь не найден: {mailing.unresolved_count}{mailing.total_requested}\n"
                        f"Ошибка отправки: {mailing.delivery_failed_count}{mailing.total_requested}\n")
        return mailing_info
    await callback.message.edit_text(
        LEXICON["ADMIN"]["MAILING"]["mailing_info"].format(
            mailing.created_at.strftime("%d.%m.%Y %H:%M:%S"),
            mailing.finished_at - mailing.started_at,
            compute_mailing_info()
        ),
        reply_markup=get_mailing_info_inline_kb(
            mailing,
            mailing.template_id,
        )
    )


@router.callback_query(MailingTemplateViewData.filter(F.action == "view"))
async def handle_check_mailing_template(
        callback: CallbackQuery,
        callback_data: MailingTemplateViewData,
        session: AsyncSession,
):
    template_id, mailing_id = callback_data.id, callback_data.mailing_id
    template = await Template.get(
        session=session,
        primary_key=template_id,
        history_get=True
    )
    mailing = await Mailing.get(
        session=session,
        primary_key=mailing_id,
    )

    template_info = LEXICON["ADMIN"]["TEMPLATE"]['template_info'].format(
        template.name,
        template.formated_description
    )

    await callback.message.edit_text(
        text=template_info,
        reply_markup=get_mailing_template_view_kb(
            mailing.id
        )
    )


# @router.callback_query(MailingTemplateViewData.filter(F.action == "back"))
# async def handle_back_from_mailing_template(
#         callback: CallbackQuery,
#         callback_data: MailingTemplateViewData,
#         session: AsyncSession,
#         admin: User
# ):
#     template_id, mailing_id = callback_data.id, callback_data.mailing_id
#     template = await Template.get(
#         session=session,
#         primary_key=template_id,
#     )
#     mailing = await Mailing.get(
#         session=session,
#         primary_key=mailing_id,
#     )
#
#     await callback.message.edit_text(
#         text=...,
#         reply_markup=get_mailing_template_view_kb(
#             template.id,
#             mailing.id
#         )
#     )

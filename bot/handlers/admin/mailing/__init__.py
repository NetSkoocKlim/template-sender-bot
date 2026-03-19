import asyncio
import datetime
import logging

from aiogram import  F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from aiogram.exceptions import TelegramRetryAfter


from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.template.edit import get_templates_list
from bot.keyboards.admin.constants import AdminPanelOptions, AdminPanelMailingOptions, AdminPanelChosenTemplateOptions

from bot.keyboards.admin.menu import (get_admin_panel_mailing_menu_kb,
                                      get_admin_panel_chosen_template_kb)
from bot.lexicon import LEXICON
from database.models import User, Template, Mailing, Receiver
from redis.asyncio import Redis

from database.redis.redis_keys import admin_chosen_mailing_template_key
from bot.utils import create_mailing_result_csv
from services.object_storage_app.app import ObjectStorageApp

router = Router()
logger = logging.getLogger(__name__)
@router.callback_query(F.data == AdminPanelOptions.mailing.name)
@router.callback_query(F.data == AdminPanelChosenTemplateOptions.back2mlng.name)
async def handle_admin_mailing_menu(callback: CallbackQuery,
                                    admin: User,
                                    session: AsyncSession):
    chosen_template = await Template.get_by_filter(
        session=session,
        creator_id=admin.id,
        is_chosen_for_mailing=True
    )
    if not chosen_template:
        await callback.answer("Перед началом рассылки необходимо выбрать шаблон")
        return
    saved_receivers_count = await Receiver.count_total(
        session=session,
        filter_by={
            "admin_id": admin.id,
        }
    )
    if saved_receivers_count == 0:
        await callback.answer("Перед началом рассылки необходимо указать список пользователей")
        return
    template_name = chosen_template.name

    mailing_info_text = LEXICON["ADMIN"]["MAILING"]["main"].format(
        saved_receivers_count,
        template_name
    )
    await callback.answer()
    await callback.message.edit_text(text=mailing_info_text,
                         reply_markup=get_admin_panel_mailing_menu_kb())


@router.callback_query(F.data == AdminPanelMailingOptions.view_chosen_template.name)
async def handle_choose_template_menu(callback: CallbackQuery, admin: User,
                                      session: AsyncSession):
    template = await Template.get_by_filter(
        session=session,
        creator_id=admin.id,
        is_chosen_for_mailing=True
    )
    template_info = "Для рассылки будет использоваться следующий шаблон:\n\n" + LEXICON["ADMIN"]["TEMPLATE"]["template_info"].format(
        template.name,
        template.formated_description
    )
    await callback.answer()
    await callback.message.edit_text(text=template_info, reply_markup=get_admin_panel_chosen_template_kb())


@router.callback_query(F.data == AdminPanelChosenTemplateOptions.choose_another.name)
async def handle_choose_another_template_button(callback: CallbackQuery, admin: User,
                                                session: AsyncSession):
    await get_templates_list(callback.message, admin.id, session)


def format_mailing_report(total: int,
                         unresolved_usernames: list[str],
                         failed_usernames: list[str],
                         max_list=10) -> str:
    not_found = len(unresolved_usernames)
    failed = len(failed_usernames)
    lines = ["📣 Результат рассылки\n"]

    if not_found == 0 and failed == 0:
        lines.append(f"Сообщение успешно доставлено всем указанным пользователям")
        return "\n".join(lines)
    lines.append(f"Успешно доставлено: {total - not_found - failed}/{total}")
    lines.append(f"Не найдено username: {not_found}")
    lines.append(f"Не доставлено: {failed}\n")

    if unresolved_usernames:
        shown = unresolved_usernames[:max_list]
        lines.append("Проблемные username (никогда не взаимодействовали с ботом, либо сменили свой username):")
        lines.extend(shown)
        if len(unresolved_usernames) > max_list:
            lines.append(f"...и ещё {len(unresolved_usernames)-max_list} скрыто(ых)")

    if failed_usernames:
        lines.append("\nСписок недоставленных (ошибки отправки):")
        shown = failed_usernames[:max_list]
        lines.extend(shown)
        if len(failed_usernames) > max_list:
            lines.append(f"...и ещё {len(failed_usernames)-max_list} скрыто(ых)")

    return "\n".join(lines)


MAX_RETRIES = 5
BASE_RETRY_DELAY = 1.0

@router.callback_query(F.data == AdminPanelMailingOptions.begin_mailing.name)
async def handle_begin_mailing_button(callback: CallbackQuery, admin: User,
                                      redis: Redis,
                                      session: AsyncSession,
                                      s3_storage: ObjectStorageApp):
    chosen_template = await Template.get_by_filter(
        session=session,
        creator_id=admin.id,
        is_chosen_for_mailing=True
    )
    if not chosen_template:
        await callback.answer("Перед началом рассылки необходимо выбрать шаблон")
        return

    receivers = await Receiver.all_by_filter(
        session=session,
        admin_id=admin.id,
    )
    if not receivers:
        await callback.answer("Вы не сохранили ни одного юзернейма, кому необходимо будет отправить сообщение")
        return

    user_list_length = len(receivers)
    usernames = [receiver.username for receiver in receivers]
    receivers_ids = await User.get_ids_by_usernames(session=session, usernames=usernames)
    unresolved_usernames = ["@"+u for u, uid in zip(usernames, receivers_ids) if uid is None]
    failed_usernames = []
    success_usernames = []
    started_at = datetime.datetime.now()
    for receiver_username, receiver_id in zip(usernames, receivers_ids):
        if receiver_id is None:
            continue
        receiver_username = '@' + receiver_username
        attempt = 0
        while True:
            try:
                await callback.bot.send_message(
                    chat_id=receiver_id,
                    text=chosen_template.formated_description
                )
                success_usernames.append(receiver_username)
                break
            except TelegramRetryAfter as e:
                wait_for = getattr(e, "retry_after", None) or (BASE_RETRY_DELAY * attempt)
                logger.warning("TelegramRetryAfter for %s: waiting %.1f sec (attempt %d)",
                            receiver_username, wait_for, attempt + 1)
                await asyncio.sleep(wait_for + 0.5)
                if attempt > MAX_RETRIES:
                    logger.error("Max retries exceeded for %s after RetryAfter", receiver_username)
                    failed_usernames.append(receiver_username)
                    break
            except Exception as e:
                attempt += 1
                if attempt > MAX_RETRIES:
                    logger.error("Unexpected error, giving up on %s", e, receiver_username)
                    failed_usernames.append(receiver_username)
                    break
                delay = BASE_RETRY_DELAY * (attempt-1)
                logger.warning("Unexpected error sending to %s: %s — retrying in %.1f sec (attempt %d)",
                            receiver_username, e, delay, attempt)
                await asyncio.sleep(delay)
    try:
        csv_bytes = create_mailing_result_csv(
            success_usernames,
            unresolved_usernames,
            failed_usernames,
        )
        key = f"mailing-result-{admin.id}-{int(datetime.datetime.now().timestamp())}"
        await s3_storage.upload_file(csv_bytes.getvalue(), key)
    except Exception as e:
        logger.error(f"Failed to save mailing result {e}")
        key = None
    finished_at = datetime.datetime.now()
    await Mailing.create(
        session=session,
        admin_id=admin.id,
        template_id=int(chosen_template.id),
        started_at=started_at,
        finished_at=finished_at,
        total_requested=user_list_length,
        unresolved_count=len(unresolved_usernames),
        delivery_failed_count=len(failed_usernames),
        csv_result_key=key
    )
    report = format_mailing_report(
        total=user_list_length,
        unresolved_usernames=unresolved_usernames,
        failed_usernames=failed_usernames
    )
    await callback.message.edit_text(text=report,
                                     reply_markup=InlineKeyboardMarkup(
                                         inline_keyboard=[ [
                                             InlineKeyboardButton(
                                                 text=AdminPanelOptions.back,
                                                 callback_data=AdminPanelOptions.back.name,
                                             )
                                             ]
                                         ]
                                     ))
    await callback.answer()
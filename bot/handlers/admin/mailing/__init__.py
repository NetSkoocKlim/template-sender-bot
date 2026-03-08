import datetime

import aiohttp
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.template.edit import get_templates_list
from bot.keyboards import AdminPanelOptions
from bot.keyboards.admin_keyboards import get_admin_panel_mailing_menu_kb, AdminPanelMailingOptions, \
    get_admin_panel_chosen_template_kb, AdminPanelChosenTemplateOptions, get_admin_panel_template_menu_kb, \
    get_admin_panel_receiver_menu_kb, get_admin_panel_menu_kb
from bot.lexicon import LEXICON
from database.models import User, Template, Mailing, Receiver
from redis.asyncio import Redis

from database.redis import admin_receivers_key
from database.redis.redis_keys import admin_chosen_mailing_template_key
from bot.utils import create_mailing_result_csv


router = Router()

@router.callback_query(F.data == AdminPanelOptions.mailing)
@router.callback_query(F.data == AdminPanelChosenTemplateOptions.back)
async def handle_admin_mailing_menu(callback: CallbackQuery,
                                    redis: Redis,
                                    admin: User,
                                    session: AsyncSession):
    chosen_template = await Template.get_by_filter(
        session=session,
        admin_id=admin.id,
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
    template_name = Template.name

    mailing_info_text = LEXICON["ADMIN"]["MAILING"]["main"].format(
        saved_receivers_count,
        template_name
    )
    await callback.answer()
    await callback.message.edit_text(text=mailing_info_text,
                         reply_markup=get_admin_panel_mailing_menu_kb())


@router.callback_query(F.data == AdminPanelMailingOptions.view_chosen_template)
async def handle_choose_template_menu(callback: CallbackQuery, admin: User,
                                      redis: Redis,
                                      session: AsyncSession):
    chosen_template = await redis.get(admin_chosen_mailing_template_key(admin.id))
    template_index, template_id, _ = chosen_template.split(":")
    template = await Template.get(session, int(template_id))
    template_info = "Для рассылки будет использоваться следующий шаблон:\n\n" + LEXICON["ADMIN"]["TEMPLATE"]["template_info"].format(
        template.name,
        template.formated_description
    )
    await callback.answer()
    await callback.message.edit_text(text=template_info, reply_markup=get_admin_panel_chosen_template_kb())


@router.callback_query(F.data == AdminPanelChosenTemplateOptions.choose_another)
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


@router.callback_query(F.data == AdminPanelMailingOptions.begin_mailing)
async def handle_begin_mailing_button(callback: CallbackQuery, admin: User,
                                      redis: Redis,
                                      session: AsyncSession):
    chosen_template = await Template.get_by_filter(
        session=session,
        admin_id=admin.id,
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
    unresolved_usernames = [u for u, uid in zip(usernames, receivers_ids) if uid is None]
    failed_usernames = []
    success_usernames = []
    started_at = datetime.datetime.now()
    for receiver_username, receiver_id in zip(usernames, receivers_ids):
        if receiver_id is None:
            continue
        try:
            await callback.bot.send_message(
                chat_id=receiver_id,
                text=chosen_template.formated_description
            )
            success_usernames.append(receiver_username)
        except Exception as e:
            failed_usernames.append(receiver_username)

    finished_at = datetime.datetime.now()

    created_result = await Mailing.create(
        session=session,
        admin_id=admin.id,
        template_id=int(chosen_template.id),
        started_at=started_at,
        finished_at=finished_at,
        total_requested=user_list_length,
        unresolved_count=len(unresolved_usernames),
        delivery_failed_count=len(failed_usernames)
    )

    try:
        data = aiohttp.FormData()

        csv_bytes = create_mailing_result_csv(
            success_usernames,
            unresolved_usernames,
            failed_usernames,
        )

        data.add_field("file",
                       csv_bytes,
                       filename=f"mailing-result-"
                                f"{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}"
                                f".csv_bytes",
                       content_type="application/octet-stream")
        key = f"mailing-result-{created_result.id}"
        data.add_field("key", key)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://127.0.0.1:8004/buckets",
                data=data
            ) as response:
                if response.status != 200 and response.status != 201:
                    raise
    except Exception as e:
        key = None
    setattr(created_result, "csv_result_key", key)

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
                                                 callback_data=AdminPanelOptions.back,
                                             )
                                             ]
                                         ]
                                     ))
    await callback.answer()
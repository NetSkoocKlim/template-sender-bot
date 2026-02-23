import json

import sqlalchemy
from aiogram import Router, F, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.template.add import MAX_TEMPLATE_NAME_LENGTH, MAX_TEMPLATE_DESCRIPTION_LENGTH
from bot.keyboards.admin_keyboards import AdminPanelTemplateOptions, get_templates_inline_kb, PaginateButtonData, \
    TemplateEditData, TemplateEditAction, get_template_edit_inline_kb
from bot.keyboards.common import get_cancel_button
from bot.lexicon import LEXICON
from bot.states.states import TemplateEditStates
from bot.utils.copy_message import copy_text_message
from database.models import Template, User
from database.models.base import Anchor
from database.redis import get_redis
from database.redis.redis_keys import admin_chosen_mailing_template_key

router = Router()

async def _save_page_anchor_to_redis(admin_id: int, anchor: Anchor, direction: int, page_count):
    """
    Сохраняет в redis snapshot для конкретной страницы:
    key: admin{admin_id}:templates:page:{page}
    value: json {"anchor_page":.., "anchor_value":.., "direction":..}
    """
    r = get_redis()
    if r is None:
        return
    key = f"admin:{admin_id}:templates:page"
    payload = {
        "anchor_page": anchor.page,
        "anchor_value": anchor.value,
        "direction": direction,
        "page_count": page_count
    }
    await r.set(key, json.dumps(payload), ex=3600)


async def _get_page_anchor_from_redis(admin_id: int) -> tuple[Anchor, int, int] | None:
    r = get_redis()
    if r is None:
        return None
    key = f"admin:{admin_id}:templates:page"
    raw = await r.get(key)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return (Anchor(page=int(data.get("anchor_page", 1)), value=int(data.get("anchor_value", 0))),
                int(data.get("direction", 1)),
                int(data.get("page_count", 1)))
    except Exception:
        return None


async def get_templates_list(
        message: Message,
        template_creator_id: int,
        session: AsyncSession,
        page_count: int = 1,
        anchor: Anchor = Anchor(),
        direction: int = 1,
        is_deletion: bool = False
    ):
    filters = [sqlalchemy.text(f"templates.creator_id={template_creator_id}")]
    templates, backward_anchor, forward_anchor = await Template.paginate_fast(
        is_deletion=is_deletion,
        session=session,
        anchor=anchor,
        direction=direction,
        page=anchor.page,
        filters=filters
    )

    try:
        await _save_page_anchor_to_redis(template_creator_id, anchor, direction, page_count)
    except Exception as e:
        print(e)

    chosen_template = await get_redis().get(admin_chosen_mailing_template_key(template_creator_id)) if get_redis() else None
    chosen_template_id = None
    if chosen_template:
        chosen_template_id = chosen_template.split(':')[1]
    try:
        await message.edit_text(LEXICON["ADMIN"]["TEMPLATE"]["templates_list"],
                             reply_markup=get_templates_inline_kb(templates,
                                                                  chosen_template_id=chosen_template_id,
                                                                  forward_anchor=forward_anchor,
                                                                  backward_anchor=backward_anchor,
                                                                  page_count=page_count,
                                                                  page=anchor.page))
    except TelegramBadRequest as e:
        await message.answer(LEXICON["ADMIN"]["TEMPLATE"]["templates_list"],
                                reply_markup=get_templates_inline_kb(templates,
                                                                     chosen_template_id=chosen_template_id,
                                                                     forward_anchor=forward_anchor,
                                                                     backward_anchor=backward_anchor,
                                                                     page_count=page_count,
                                                                     page=anchor.page))


@router.callback_query(F.data == AdminPanelTemplateOptions.edit_template)
async def handle_edit_template_button(callback: CallbackQuery, session: AsyncSession, admin: User):
    try:
        pages_count = await Template.total_pages(
            session=session,
            filters=[sqlalchemy.text(f"templates.creator_id={admin.id}")],
        )
        await get_templates_list(callback.message, admin.id, session, page_count=pages_count)
    except Exception as e:
        await callback.message.answer(f"Something went wrong. {e}")


@router.callback_query(PaginateButtonData.filter(F.model == "Template"))
async def handle_pagination(callback: CallbackQuery,
                            callback_data: PaginateButtonData,
                            session: AsyncSession,
                            admin: User):
    anchor = Anchor(page=callback_data.anchor_page, value=callback_data.anchor_value)
    direction = callback_data.direction
    await callback.answer()
    await get_templates_list(callback.message,
                             session=session,
                             template_creator_id=admin.id,
                             direction=direction,
                             anchor=anchor,
                             page_count=callback_data.page_count
                             )


@router.callback_query(F.data == "empty_pagination")
async def handle_empty_pagination(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(TemplateEditData.filter(F.action == TemplateEditAction.view))
async def handle_template_edit(callback: CallbackQuery, session: AsyncSession, callback_data: TemplateEditData):
    try:
        template = await Template.get(session=session, primary_key=callback_data.id)

        if not template:
            await callback.message.answer(text="Шаблон не найден или был удалён.")
            return
        template_info = html.bold(html.italic("✅ Выбран для рассылки ✅\n\n")) if callback_data.is_chosen else ""
        template_info = template_info + LEXICON["ADMIN"]["TEMPLATE"]['template_info'].format(callback_data.index,
                                                                             template.name,
                                                                             template.formated_description)
        await callback.message.edit_text(
            text=template_info,
            reply_markup=get_template_edit_inline_kb(
                template=template,
                template_is_chosen=callback_data.is_chosen,
                template_index=callback_data.index
            )
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Failed to load template data. {e}", show_alert=True)

@router.callback_query(TemplateEditData.filter(F.action == TemplateEditAction.edit_name), default_state)
async def handle_template_edit_name(callback: CallbackQuery, state: FSMContext, callback_data: TemplateEditData):
    await callback.answer()
    await state.update_data(template_id=callback_data.id, template_index=callback_data.index,
                            template_is_chosen=callback_data.is_chosen,)
    await state.set_state(TemplateEditStates.template_name)
    await callback.message.edit_text(
        "Введите новое название для шаблона",
        reply_markup=get_cancel_button()
    )

@router.message(F.text, TemplateEditStates.template_name)
async def handle_new_template_name(message: Message, state: FSMContext, session: AsyncSession):
    new_template_name = message.text.strip()
    if len(new_template_name) > MAX_TEMPLATE_NAME_LENGTH:
        await message.answer(f"Длина названия не должна превышать {MAX_TEMPLATE_NAME_LENGTH}."
                             f" Придумайте другое название")
        return
    template_data = (await state.get_data())
    template_id, template_index, template_is_chosen = (
        template_data["template_id"],
        template_data["template_index"],
        template_data["template_is_chosen"]
    )
    try:
        updated_template = await Template.update(session=session, primary_key=template_id, name=new_template_name)
        if not updated_template:
            await message.answer("Редактируемый шаблон не найден", reply_markup=ReplyKeyboardRemove())
            await get_templates_list(message, message.from_user.id, session)
            return
        await message.answer("Название шаблона успешно изменено")
        new_template_info = html.bold(html.italic("✅ Выбран для рассылки ✅\n\n")) if template_is_chosen else ""
        new_template_info = new_template_info + LEXICON["ADMIN"]["TEMPLATE"]['template_info'].format(
            template_index,
            new_template_name,
            updated_template.formated_description
        )
        await message.answer(new_template_info,
                             reply_markup=get_template_edit_inline_kb(template=updated_template,
                                                                      template_is_chosen=template_is_chosen,
                                                                      template_index=template_index))
    except Exception as e:
        await message.answer(f"Не удалось изменить название шаблона. {e}")
        await get_templates_list(message, message.from_user.id, session)
    finally:
        await state.clear()


@router.message(TemplateEditStates.template_name)
async def handle_wrong_new_template_name(message: Message):
    await message.answer("Название шаблона должно быть текстом", reply_markup=get_cancel_button())

@router.callback_query(TemplateEditData.filter(F.action == TemplateEditAction.delete), default_state)
async def handle_template_delete(callback: CallbackQuery, session: AsyncSession, callback_data: TemplateEditData,
                                 redis: Redis,
                                 admin: User):
    try:
        template_to_delete = await Template.update(session=session, primary_key=callback_data.id, is_active=False)
        if callback_data.is_chosen:
            await redis.delete(admin_chosen_mailing_template_key(admin.id))
        if not template_to_delete:
            raise Exception("Шаблон уже был удалён")
        saved = await _get_page_anchor_from_redis(admin.id)
        anchor, direction, saved_page_count = saved
        pages_count_after_deleting = await Template.total_pages(
            session=session,
            filters=[sqlalchemy.text(f"templates.creator_id={admin.id}")],
        )
        saved_page_count = min(pages_count_after_deleting, saved_page_count)
        if anchor.page > saved_page_count:
            anchor = Anchor(page=saved_page_count, value=template_to_delete.id)
            direction = 0

        await callback.answer("Шаблон успешно удалён")
        await get_templates_list(
            callback.message,
            session=session,
            anchor=anchor,
            template_creator_id=admin.id,
            page_count=saved_page_count,
            direction=direction,
            is_deletion=True
        )
    except Exception as e:
        await callback.answer(f"Не удалось удалить данный шаблон. {e}")
        await get_templates_list(callback.message, callback_data.creator_id, session)

@router.callback_query(TemplateEditData.filter(F.action == TemplateEditAction.edit_description), default_state)
async def handle_template_edit_description(callback: CallbackQuery, state: FSMContext, callback_data: TemplateEditData):
    await state.update_data(template_id=callback_data.id, template_index=callback_data.index,
                            template_is_chosen=callback_data.is_chosen)
    await state.set_state(TemplateEditStates.template_description)
    await callback.answer()
    await callback.message.edit_text(
        "Введите новое описание для шаблона.",
        reply_markup=get_cancel_button()
    )

@router.message(F.text, TemplateEditStates.template_description)
async def handle_new_template_description(message: Message, state: FSMContext, session: AsyncSession):
    new_template_description = message.text.strip()
    if len(new_template_description) > MAX_TEMPLATE_DESCRIPTION_LENGTH:
        await message.answer(f"Длина описания не должна превышать {MAX_TEMPLATE_DESCRIPTION_LENGTH}."
                             f" Придумайте другое название",
                             reply_markup=get_cancel_button())
        return
    template_data = await state.get_data()
    template_id, template_index, template_is_chosen = (
        template_data["template_id"],
        template_data["template_index"],
        template_data["template_is_chosen"]
    )
    try:
        updated_template = await Template.update(
                                session=session,
                                primary_key=template_id,
                                description=new_template_description,
                                formated_description=copy_text_message(new_template_description, message.entities))

        if not updated_template:
            raise Exception("Редактируемый шаблон не найден или был удалён")
        await message.answer("Описание шаблона успешно изменено")
        new_template_info = html.bold(html.italic("✅ Выбран для рассылки ✅\n\n")) if template_is_chosen else ""
        new_template_info = new_template_info + LEXICON["ADMIN"]["TEMPLATE"]['template_info'].format(
            template_index,
            updated_template.name,
            new_template_description
        )
        await message.answer(new_template_info,
                             reply_markup=get_template_edit_inline_kb(template=updated_template,
                                                                      template_is_chosen=template_data["template_is_chosen"],
                                                                      template_index=template_index))
    except Exception as e:
        await message.answer(f"Не удалось изменить описание шаблона. {e}")
        await get_templates_list(message, message.from_user.id, session)

    finally:
        await state.clear()

@router.message(TemplateEditStates.template_description)
async def handle_wrong_new_template_description(message: Message):
    await message.answer("Описание шаблона должно быть текстом", reply_markup=get_cancel_button())


@router.callback_query(TemplateEditData.filter(F.action == TemplateEditAction.back_to_list))
async def handle_back_to_templates(callback: CallbackQuery, session: AsyncSession,
                                   admin: User):
    await callback.answer()

    saved = await _get_page_anchor_from_redis(admin.id)
    anchor, direction, page_count = saved

    await get_templates_list(
        callback.message,
        session=session,
        anchor=anchor,
        template_creator_id=admin.id,
        page_count=page_count,
        direction=direction,
    )

@router.callback_query(TemplateEditData.filter(F.action == TemplateEditAction.choose))
async def handle_choose_template_button(callback: CallbackQuery, callback_data: TemplateEditData, redis: Redis,
                                        admin: User, session: AsyncSession):
    await redis.set(admin_chosen_mailing_template_key(admin.id), f"{callback_data.index}:{callback_data.id}:{callback_data.name}")

    saved = await _get_page_anchor_from_redis(admin.id)
    if saved:
        anchor, direction, page_count = saved
    else:
        anchor = Anchor(page=1, value=0)
        direction = 1
        page_count = 1

    await get_templates_list(
        callback.message,
        session=session,
        anchor=anchor,
        template_creator_id=admin.id,
        page_count=page_count,
        direction=direction,
    )
    await callback.answer("Шаблон для рассылки успешно изменён.")


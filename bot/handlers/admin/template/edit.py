import math

import sqlalchemy
from aiogram import Router, F, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import default_state
from aiogram.types import Message, CallbackQuery
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.admin_keyboards import AdminPanelTemplateOptions, get_templates_inline_kb, PaginateButtonData, \
    TemplateEditData, TemplateEditAction, get_template_edit_inline_kb
from bot.lexicon import LEXICON
from database.models import Template, User
from database import TemplatePaginator
from database.paginator.anchor_store import store_payload_with_token, retrieve_payload_by_token, \
    store_page_anchor_state, get_page_anchor_state

from database.redis import get_redis
from database.redis.redis_keys import admin_chosen_mailing_template_key


router = Router()


async def get_templates_list(
        message: Message,
        template_creator_id: int,
        session: AsyncSession,
        anchor: str | None = None,
        forward: bool = True,
        is_deletion: bool = False,
        is_back: bool = False
    ):
    if anchor and not is_back and not is_deletion:
        anchor = await retrieve_payload_by_token(anchor, template_creator_id)
    filters = [sqlalchemy.text(f"templates.creator_id={template_creator_id}")]
    stmt = Template.get_select_statement(filters=filters)
    templates, backward_anchor, forward_anchor, current_page, total_pages = await TemplatePaginator.paginate_page(
        session=session, base_stmt=stmt, anchor=anchor, forward=forward, is_deletion=is_deletion)
    ext_backward = None
    ext_forward = None
    if backward_anchor and current_page != 1:
        ext_backward = await store_payload_with_token(backward_anchor, template_creator_id)
    if forward_anchor and current_page != total_pages:
        ext_forward = await store_payload_with_token(forward_anchor, template_creator_id)
    try:
        await store_page_anchor_state(template_creator_id, anchor, forward, current_page)
    except Exception as e:
        print(e)
    try:
        await message.edit_text(LEXICON["ADMIN"]["TEMPLATE"]["templates_list"],
                             reply_markup=get_templates_inline_kb(templates,
                                                                  forward_anchor=ext_forward,
                                                                  backward_anchor=ext_backward,
                                                                  page_count=total_pages,
                                                                  page=current_page))
    except TelegramBadRequest as e:
        await message.answer(LEXICON["ADMIN"]["TEMPLATE"]["templates_list"],
                                reply_markup=get_templates_inline_kb(
                                    templates,
                                    forward_anchor=ext_backward,
                                    backward_anchor=ext_backward,
                                    page_count=total_pages,
                                    page=current_page
                                )
                             )
    except Exception as e:
        print(e)


@router.callback_query(F.data == AdminPanelTemplateOptions.edit_template)
async def handle_edit_template_button(callback: CallbackQuery, session: AsyncSession, admin: User):
    try:
        await get_templates_list(callback.message, admin.id, session)
    except Exception as e:
        await callback.answer(f"Something went wrong.")


@router.callback_query(PaginateButtonData.filter())
async def handle_pagination(callback: CallbackQuery,
                            callback_data: PaginateButtonData,
                            session: AsyncSession,
                            admin: User):
    anchor = callback_data.anchor
    forward = callback_data.forward
    await callback.answer()
    await get_templates_list(
        callback.message,
        session=session,
        template_creator_id=admin.id,
        forward=forward,
        anchor=anchor
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
                template_index=callback_data.index
            )
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Failed to load template data. {e}", show_alert=True)

# @router.callback_query(TemplateEditData.filter(F.action == TemplateEditAction.edit_name), default_state)
# async def handle_template_edit_name(callback: CallbackQuery, state: FSMContext, callback_data: TemplateEditData):
#     await callback.answer()
#     await state.update_data(template_id=callback_data.id, template_index=callback_data.index,
#                             template_is_chosen=callback_data.is_chosen,)
#     await state.set_state(TemplateEditStates.template_name)
#     await callback.message.edit_text(
#         "Введите новое название для шаблона",
#         reply_markup=get_cancel_button()
#     )

# @router.message(F.text, TemplateEditStates.template_name)
# async def handle_new_template_name(message: Message, state: FSMContext, session: AsyncSession):
#     new_template_name = message.text.strip()
#     if len(new_template_name) > MAX_TEMPLATE_NAME_LENGTH:
#         await message.answer(f"Длина названия не должна превышать {MAX_TEMPLATE_NAME_LENGTH}."
#                              f" Придумайте другое название")
#         return
#     template_data = (await state.get_data())
#     template_id, template_index, template_is_chosen = (
#         template_data["template_id"],
#         template_data["template_index"],
#         template_data["template_is_chosen"]
#     )
#     try:
#         updated_template = await Template.update(session=session, primary_key=template_id, name=new_template_name)
#         if not updated_template:
#             await message.answer("Редактируемый шаблон не найден", reply_markup=ReplyKeyboardRemove())
#             await get_templates_list(message, message.from_user.id, session)
#             return
#         await message.answer("Название шаблона успешно изменено")
#         new_template_info = html.bold(html.italic("✅ Выбран для рассылки ✅\n\n")) if template_is_chosen else ""
#         new_template_info = new_template_info + LEXICON["ADMIN"]["TEMPLATE"]['template_info'].format(
#             template_index,
#             new_template_name,
#             updated_template.formated_description
#         )
#         await message.answer(new_template_info,
#                              reply_markup=get_template_edit_inline_kb(template=updated_template,
#                                                                       template_is_chosen=template_is_chosen,
#                                                                       template_index=template_index))
#     except Exception as e:
#         await message.answer(f"Не удалось изменить название шаблона. {e}")
#         await get_templates_list(message, message.from_user.id, session)
#     finally:
#         await state.clear()


# @router.message(TemplateEditStates.template_name)
# async def handle_wrong_new_template_name(message: Message):
#     await message.answer("Название шаблона должно быть текстом", reply_markup=get_cancel_button())

# @router.callback_query(TemplateEditData.filter(F.action == TemplateEditAction.edit_desc), default_state)
# async def handle_template_edit_description(callback: CallbackQuery, state: FSMContext, callback_data: TemplateEditData):
#     await state.update_data(template_id=callback_data.id, template_index=callback_data.index,
#                             template_is_chosen=callback_data.is_chosen)
#     await state.set_state(TemplateEditStates.template_description)
#     await callback.answer()
#     await callback.message.edit_text(
#         "Введите новое описание для шаблона.",
#         reply_markup=get_cancel_button()
#     )
#
# @router.message(F.text, TemplateEditStates.template_description)
# async def handle_new_template_description(message: Message, state: FSMContext, session: AsyncSession):
#     new_template_description = message.text.strip()
#     if len(new_template_description) > MAX_TEMPLATE_DESCRIPTION_LENGTH:
#         await message.answer(f"Длина описания не должна превышать {MAX_TEMPLATE_DESCRIPTION_LENGTH}."
#                              f" Придумайте другое название",
#                              reply_markup=get_cancel_button())
#         return
#     template_data = await state.get_data()
#     template_id, template_index, template_is_chosen = (
#         template_data["template_id"],
#         template_data["template_index"],
#         template_data["template_is_chosen"]
#     )
#     try:
#         updated_template = await Template.update(
#                                 session=session,
#                                 primary_key=template_id,
#                                 description=new_template_description,
#                                 formated_description=copy_text_message(new_template_description, message.entities))
#
#         if not updated_template:
#             raise Exception("Редактируемый шаблон не найден или был удалён")
#         await message.answer("Описание шаблона успешно изменено")
#         new_template_info = html.bold(html.italic("✅ Выбран для рассылки ✅\n\n")) if template_is_chosen else ""
#         new_template_info = new_template_info + LEXICON["ADMIN"]["TEMPLATE"]['template_info'].format(
#             template_index,
#             updated_template.name,
#             new_template_description
#         )
#         await message.answer(new_template_info,
#                              reply_markup=get_template_edit_inline_kb(template=updated_template,
#                                                                       template_is_chosen=template_data["template_is_chosen"],
#                                                                       template_index=template_index))
#     except Exception as e:
#         await message.answer(f"Не удалось изменить описание шаблона. {e}")
#         await get_templates_list(message, message.from_user.id, session)
#
#     finally:
#         await state.clear()
#
# @router.message(TemplateEditStates.template_description)
# async def handle_wrong_new_template_description(message: Message):
#     await message.answer("Описание шаблона должно быть текстом", reply_markup=get_cancel_button())


@router.callback_query(TemplateEditData.filter(F.action == TemplateEditAction.delete), default_state)
async def handle_template_delete(callback: CallbackQuery, session: AsyncSession, callback_data: TemplateEditData,
                                 redis: Redis,
                                 admin: User):
    try:
        template_to_delete = await Template.update(session=session, primary_key=callback_data.id, is_active=False,
                                                   is_chosen_for_mailing=False)
        if not template_to_delete:
            raise Exception("Шаблон уже был удалён")
        anchor, forward, current_page = await get_page_anchor_state(admin.id)
        stmt = Template.get_select_statement(filter_by={"creator_id": admin.id})
        templates_count = await TemplatePaginator.count_total(session=session, base_stmt=stmt)
        page_count = math.ceil(templates_count / TemplatePaginator.PAGE_SIZE)
        if current_page > page_count:
            values, _ = TemplatePaginator.decode_anchor_to_values(anchor)
            anchor = TemplatePaginator.anchor_from_values(values, page_count)
            forward = False
        await get_templates_list(
            callback.message,
            session=session,
            anchor=anchor,
            template_creator_id=admin.id,
            forward=forward,
            is_deletion=True
        )
        await callback.answer("Шаблон успешно удалён")

    except Exception as e:
        await callback.answer(f"Не удалось удалить данный шаблон. {e}")
        await get_templates_list(callback.message, callback_data.creator_id, session)

@router.callback_query(TemplateEditData.filter(F.action == TemplateEditAction.bckto_lst))
async def handle_back_to_templates(callback: CallbackQuery, session: AsyncSession,
                                   admin: User):
    anchor, forward, _ = await get_page_anchor_state(admin.id)
    await get_templates_list(
        callback.message,
        session=session,
        anchor=anchor,
        template_creator_id=admin.id,
        forward=forward,
        is_back=True
    )
    await callback.answer()


@router.callback_query(TemplateEditData.filter(F.action == TemplateEditAction.choose))
async def handle_choose_template_button(callback: CallbackQuery, callback_data: TemplateEditData, redis: Redis,
                                        admin: User, session: AsyncSession):
    await Template.update(
        session=session,
        primary_key=callback_data.id,
        is_chosen_for_mailing=True
    )

    anchor, forward, _ = await get_page_anchor_state(admin.id)

    await get_templates_list(
        callback.message,
        session=session,
        anchor=anchor,
        template_creator_id=admin.id,
        forward=forward,
        is_back=True
    )
    await callback.answer("Шаблон для рассылки успешно изменён.")


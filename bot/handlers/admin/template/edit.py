import sqlalchemy
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states.states import TemplateEditStates
from database.models import Template, User
from bot.handlers.admin.template.add import MAX_TEMPLATE_NAME_LENGTH, MAX_TEMPLATE_DESCRIPTION_LENGTH
from bot.keyboards import get_admin_panel_menu_kb
from bot.keyboards.admin_keyboards import AdminPanelTemplateOptions, get_templates_inline_kb, TemplateEditData, \
    TemplateEditAction, get_template_edit_inline_kb
from bot.keyboards.common import get_cancel_reply_keyboard
from bot.lexicon import LEXICON
from bot.utils.copy_message import copy_text_message

router = Router()


async def get_templates_list(message: Message, template_creator_id: int, session: AsyncSession, page_number: int = 1):
    templates = await Template.paginate(session=session, page_number=page_number, order_by=Template.created_at,
                                        filters=[sqlalchemy.text(f"templates.creator_id={template_creator_id}"),
                                                 ])
    await message.answer("Выберите шаблон для редактирования",
                         reply_markup=get_templates_inline_kb(templates))


@router.message(F.text == AdminPanelTemplateOptions.edit_template)
async def handle_edit_template_button(message: Message, session: AsyncSession, admin: User):
    try:
        templates = await Template.all_by_filter(session=session, order_by=Template.created_at, creator_id=admin.id)
        if len(templates) == 0:
            await message.answer("У вас нет ни одного созданного шаблона", reply_markup=get_admin_panel_menu_kb())
            return
        await get_templates_list(message, message.from_user.id, session)
    except Exception as e:
        await message.answer(f"Something went wrong. {e}", reply_markup=get_admin_panel_menu_kb())


@router.callback_query(TemplateEditData.filter(F.action == TemplateEditAction.view))
async def handle_template_edit(callback: CallbackQuery, session: AsyncSession, callback_data: TemplateEditData):
    try:
        template = await Template.get(session=session, primary_key=callback_data.id)
        template_info = LEXICON["ADMIN"]["TEMPLATE"]['template_info'].format(callback_data.index,
                                                                             template.name,
                                                                             template.formated_description)
        await callback.answer()
        await callback.message.edit_text(
            text=template_info,
            reply_markup=get_template_edit_inline_kb(template=template,
                                                     template_index=callback_data.index)
        )
    except Exception as e:
        await callback.answer(f"Failed to load template data. {e}")


@router.callback_query(TemplateEditData.filter(F.action == TemplateEditAction.edit_name), default_state)
async def handle_template_edit_name(callback: CallbackQuery, state: FSMContext, callback_data: TemplateEditData):
    await callback.answer()
    await state.update_data(template_id=callback_data.id, template_index=callback_data.index)
    await state.set_state(TemplateEditStates.template_name)
    await callback.message.answer(
        "Введите новое название для шаблона",
        reply_markup=get_cancel_reply_keyboard()
    )

@router.message(F.text, TemplateEditStates.template_name)
async def handle_new_template_name(message: Message, state: FSMContext, session: AsyncSession):
    new_template_name = message.text.strip()
    if len(new_template_name) > MAX_TEMPLATE_NAME_LENGTH:
        await message.answer(f"Длина названия не должна превышать {MAX_TEMPLATE_NAME_LENGTH}."
                             f" Придумайте другое название")
        return
    template_data = (await state.get_data())
    template_id, template_index = template_data["template_id"], template_data["template_index"]
    try:
        updated_template = await Template.update(session=session, primary_key=template_id, name=new_template_name)
        if not updated_template:
            await message.answer("Редактируемый шаблон не найден", reply_markup=ReplyKeyboardRemove())
            await get_templates_list(message, message.from_user.id, session)
            return
        await message.answer("Название шаблона успешно изменено")
        new_template_info = LEXICON["ADMIN"]["TEMPLATE"]['template_info'].format(
            template_index,
            new_template_name,
            updated_template.formated_description
        )
        await message.answer(new_template_info,
                             reply_markup=get_template_edit_inline_kb(template=updated_template,
                                                                      template_index=template_index))
    except Exception as e:
        await message.answer(f"Не удалось изменить название шаблона. {e}")
        await get_templates_list(message, message.from_user.id, session)
    finally:
        await state.clear()


@router.message(TemplateEditStates.template_name)
async def handle_wrong_new_template_name(message: Message):
    await message.answer("Название шаблона должно быть текстом", reply_markup=get_cancel_reply_keyboard())


@router.callback_query(TemplateEditData.filter(F.action == TemplateEditAction.delete), default_state)
async def handle_template_delete(callback: CallbackQuery, session: AsyncSession, callback_data: TemplateEditData):
    await callback.answer()
    try:
        deleted_template = await Template.delete(session=session, primary_key=callback_data.id)
        if not deleted_template:
            raise Exception("Шаблон уже был удалён")
        await callback.message.answer("Шаблон успешно удалён")
        await callback.message.answer(LEXICON["ADMIN"]["main"], reply_markup=get_admin_panel_menu_kb())
        await callback.message.delete()
    except Exception as e:
        await callback.message.answer(f"Не удалось удалить данный шаблон. {e}")
        await get_templates_list(callback.message, callback_data.creator_id, session)


@router.callback_query(TemplateEditData.filter(F.action == TemplateEditAction.edit_description), default_state)
async def handle_template_edit_name(callback: CallbackQuery, state: FSMContext, callback_data: TemplateEditData):
    await callback.answer()
    await state.update_data(template_id=callback_data.id, template_index=callback_data.index)
    await state.set_state(TemplateEditStates.template_description)
    await callback.message.answer(
        "Введите новое описание для шаблона.",
        reply_markup=get_cancel_reply_keyboard()
    )


@router.message(F.text, TemplateEditStates.template_description)
async def handle_new_template_name(message: Message, state: FSMContext, session: AsyncSession):
    new_template_description = message.text.strip()
    if len(new_template_description) > MAX_TEMPLATE_DESCRIPTION_LENGTH:
        await message.answer(f"Длина описания не должна превышать {MAX_TEMPLATE_DESCRIPTION_LENGTH}."
                             f" Придумайте другое название",
                             reply_markup=get_cancel_reply_keyboard())
        return
    template_data = (await state.get_data())
    template_id, template_index = template_data["template_id"], template_data["template_index"]
    try:
        updated_template = await Template.update(session=session, primary_key=template_id, description=new_template_description,
                              formated_description=copy_text_message(new_template_description, message.entities))
        if not updated_template:
            raise Exception("Редактируемый шаблон не найден")

        await message.answer("Описание шаблона успешно изменено")
        new_template_info = LEXICON["ADMIN"]["TEMPLATE"]['template_info'].format(
            template_index,
            updated_template.name,
            new_template_description
        )
        await message.answer(new_template_info,
                             reply_markup=get_template_edit_inline_kb(template=updated_template,
                                                                      template_index=template_index))
    except Exception as e:
        await message.answer(f"Не удалось изменить описание шаблона. {e}")
        await get_templates_list(message, message.from_user.id, session)

    finally:
        await state.clear()


@router.message(TemplateEditStates.template_description)
async def handle_wrong_new_template_name(message: Message):
    await message.answer("Описание шаблона должно быть текстом", reply_markup=get_cancel_reply_keyboard())


@router.callback_query(TemplateEditData.filter(F.action == TemplateEditAction.to_templates_edit_list))
async def handle_back_to_edit_templates_page(callback: CallbackQuery, callback_data: TemplateEditData, session: AsyncSession):
    await callback.answer()
    await get_templates_list(callback.message, callback_data.creator_id, session)
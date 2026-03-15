from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states.states import TemplateAddStates
from database.models import Template

from bot.keyboards.admin.constants import AdminPanelTemplateOptions
from bot.keyboards.admin.menu import get_admin_panel_menu_kb

from bot.keyboards.common import get_cancel_button
from bot.lexicon import LEXICON
from bot.utils.copy_message import copy_text_message

router = Router()

MAX_TEMPLATE_NAME_LENGTH = 32
MAX_TEMPLATE_DESCRIPTION_LENGTH = 3496


@router.callback_query(F.data == AdminPanelTemplateOptions.add_template.name)
async def handle_add_template(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TemplateAddStates.template_name)
    await state.set_data({"message_id": callback.message.message_id})
    await callback.answer()
    await callback.message.edit_text(f"Задайте шаблону название. Максимальная длина названия:"
                         f" {MAX_TEMPLATE_NAME_LENGTH} символа.\n"
                         f"Название должно состоять только из букв и цифр", reply_markup=get_cancel_button())


@router.message(F.text, TemplateAddStates.template_name)
async def handle_template_name(message: Message, state: FSMContext):
    name = ' '.join(message.text.strip().split())
    state_data = await state.get_data()
    message_id = state_data.get("message_id")
    def check_symbols_in_name() -> bool:
        for sym in name:
            if not sym.isdigit() and not sym.isalpha() and not sym.isspace():
                return False
        return True
    try:
        await message.bot.delete_message(
            chat_id=message.from_user.id,
            message_id=message_id
        )
    except Exception as e:
        pass

    if len(name) > MAX_TEMPLATE_NAME_LENGTH:
        result_text = f"Слишком длинное название для шаблона. Придумайте другое"
    elif not check_symbols_in_name():
        result_text = "В названии содержатся недопустимые символы"
    else:
        result_text = (f"Введённое название: {name}\n\nТеперь отправьте описание для шаблона. Максимальная длина"
                       f" описания не должна превышать {MAX_TEMPLATE_DESCRIPTION_LENGTH} символов.")
        await state.set_state(TemplateAddStates.template_description)
    sended_message: Message =  await message.bot.send_message(
        text=result_text,
        chat_id=message.from_user.id,
        reply_markup=get_cancel_button()
    )
    await state.update_data(name=name, message_id=sended_message.message_id)



@router.message(TemplateAddStates.template_name)
async def handle_wrong_template_name(message: Message, state: FSMContext):
    state_data = await state.get_data()
    message_id = state_data.get("message_id")
    await message.bot.delete_message(
        chat_id=message.from_user.id,
        message_id=message_id
    )
    sended_message = await message.bot.send_message(
        text="Название шаблона должно быть в текстовом формате",
        chat_id=message.from_user.id,
        reply_markup=get_cancel_button()
    )
    await state.update_data(message_id=sended_message.message_id)



@router.message(F.text, TemplateAddStates.template_description)
async def handle_template_description(message: Message, state: FSMContext, session: AsyncSession):
    description = message.text.strip()
    state_data = await state.get_data()
    message_id = state_data.get("message_id")
    if len(description) > MAX_TEMPLATE_DESCRIPTION_LENGTH:
        await message.bot.delete_message(
            chat_id=message.from_user.id,
            message_id=message_id
        )
        sended_message = await message.bot.send_message(
            text=f"Длина описания не должна превышать максимально допустимое значение.",
            chat_id=message.from_user.id,
            reply_markup=get_cancel_button()
        )
        await state.update_data(message_id=sended_message.message_id)
        return
    name = state_data.get('name')
    try:
        await Template.create(session=session, name=name, description=description,
                              formated_description=copy_text_message(description, message.entities),
                              creator_id=message.from_user.id)
        await message.answer(
            text="Шаблон успешно создан",
        )
        await message.bot.delete_message(
            chat_id=message.from_user.id,
            message_id=message_id
        )
        await message.bot.send_message(
            text=LEXICON["ADMIN"]["main"],
            chat_id=message.from_user.id,
            reply_markup=get_admin_panel_menu_kb()
        )
    except Exception as e:
        await message.answer(
            text=f"При создании шаблона что-то пошло не так. {e}",
        )
        await message.bot.delete_message(
            chat_id=message.from_user.id,
            message_id=message_id
        )
        await message.bot.send_message(
            text=LEXICON["ADMIN"]["main"],
            chat_id=message.from_user.id,
            reply_markup=get_admin_panel_menu_kb()
        )
    finally:
        await state.clear()


@router.message(TemplateAddStates.template_description)
async def handle_wrong_template_description(message: Message, state: FSMContext):
    state_data = await state.get_data()
    message_id = state_data.get("message_id")
    await message.bot.delete_message(
        chat_id=message.from_user.id,
        message_id=message_id
    )
    sended_message = await message.bot.send_message(
        text="Название шаблона должно быть в текстовом формате",
        chat_id=message.from_user.id,
        reply_markup=get_cancel_button()
    )
    await state.update_data(message_id=sended_message.message_id)



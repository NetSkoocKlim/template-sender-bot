from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states.states import TemplateAddStates
from database.models import Template
from bot.keyboards import get_admin_panel_menu_kb

from bot.keyboards.admin_keyboards import AdminPanelTemplateOptions
from bot.keyboards.common import get_cancel_button
from bot.lexicon import LEXICON
from bot.utils.copy_message import copy_text_message

router = Router()

MAX_TEMPLATE_NAME_LENGTH = 32
MAX_TEMPLATE_DESCRIPTION_LENGTH = 3496


@router.callback_query(F.data == AdminPanelTemplateOptions.add_template)
async def handle_add_template(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TemplateAddStates.template_name)
    await callback.message.edit_text(f"Задайте шаблону название. Максимальная длина названия:"
                         f" {MAX_TEMPLATE_NAME_LENGTH} символа.\n"
                         f"Также название должно состоять только из букв и цифр", reply_markup=get_cancel_button())


@router.message(F.text, TemplateAddStates.template_name)
async def handle_template_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) > MAX_TEMPLATE_NAME_LENGTH:
        await message.answer(f"Слишком длинное название для шаблона. Придумайте другое", reply_markup=get_cancel_button())
        return
    def check_symbols_in_name(name_to_check: str) -> bool:
        for sym in name_to_check:
            if not sym.isdigit() and not sym.isalpha():
                return False
        return True
    if not check_symbols_in_name(name):
        await message.answer("В названии содержатся недопустимые символы", reply_markup=get_cancel_button())
        return
    await state.set_state(TemplateAddStates.template_description)
    await state.update_data(name=name)
    await message.answer(f"Отправьте описание для шаблона. Максимальная длина"
                         f"описания не должна превышать {MAX_TEMPLATE_DESCRIPTION_LENGTH} символов.",
                         reply_markup=get_cancel_button())


@router.message(TemplateAddStates.template_name)
async def handle_wrong_template_name(message: Message):
    await message.answer("Название шаблона должно быть в текстовом формате",
                         reply_markup=get_cancel_button())




@router.message(F.text, TemplateAddStates.template_description)
async def handle_template_description(message: Message, state: FSMContext, session: AsyncSession):
    description = message.text.strip()
    if len(description) > MAX_TEMPLATE_DESCRIPTION_LENGTH:
        await message.answer(f"Длина описания не должна превышать максимально допустимое значение.",
                             reply_markup=get_cancel_button())
        return
    name = (await state.get_data()).get('name')
    try:
        await Template.create(session=session, name=name, description=description,
                              formated_description=copy_text_message(description, message.entities),
                              creator_id=message.from_user.id)
        await message.answer(text="Шаблон успешно создан")
        await message.answer(text=LEXICON["ADMIN"]["main"], reply_markup=get_admin_panel_menu_kb())
    except Exception as e:
        await message.answer(f"При создании шаблона что-то пошло не так. {e}")
        await message.answer(text=LEXICON["ADMIN"]["main"], reply_markup=get_admin_panel_menu_kb())
    finally:
        await state.clear()


@router.message(TemplateAddStates.template_description)
async def handle_wrong_template_description(message: Message):
    await message.answer("Описание должно быть в текстовом формате", reply_markup=get_cancel_button())



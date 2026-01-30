from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database import DBHelper
from database.models import Template
from bot.filters import IsAdmin
from bot.keyboards import get_admin_panel_menu_kb

from bot.keyboards.admin_keyboards import AdminPanelTemplateOptions
from bot.keyboards.common import get_cancel_reply_keyboard
from bot.lexicon import LEXICON
from bot.utils.copy_message import copy_text_message

router = Router()

MAX_TEMPLATE_NAME_LENGTH = 128
MAX_TEMPLATE_DESCRIPTION_LENGTH = 3496


class TemplateAddStates(StatesGroup):
    template_name = State()
    template_description = State()


@router.message(F.text == AdminPanelTemplateOptions.add_template, IsAdmin())
async def handle_add_template(message: Message, state: FSMContext):
    await state.set_state(TemplateAddStates.template_name)
    await message.answer(f"Задайте шаблону название. Максимальная длина названия"
                         f"составляет {MAX_TEMPLATE_NAME_LENGTH} символов.", reply_markup=get_cancel_reply_keyboard())


@router.message(F.text, TemplateAddStates.template_name)
async def handle_template_name(message: Message, state: FSMContext):
    await state.set_state(TemplateAddStates.template_description)
    name = message.text.strip()
    if len(name) > MAX_TEMPLATE_NAME_LENGTH:
        await message.answer(f"Слишком длинное название для шаблона", reply_markup=get_cancel_reply_keyboard())
        return
    await state.update_data(name=name)
    await message.answer(f"Отправьте описание для шаблона. Максимальная длина"
                         f"описания не должна превышать {MAX_TEMPLATE_DESCRIPTION_LENGTH} символов.", reply_markup=get_cancel_reply_keyboard())


@router.message(TemplateAddStates.template_name)
async def handle_wrong_template_name(message: Message):
    await message.answer("Название шаблона должно быть в текстовом формате", reply_markup=get_cancel_reply_keyboard())


@router.message(F.text, TemplateAddStates.template_description)
@DBHelper.get_session
async def handle_template_description(message: Message, state: FSMContext, session: AsyncSession):
    await state.set_state(TemplateAddStates.template_description)
    description = message.text.strip()
    if len(description) > MAX_TEMPLATE_DESCRIPTION_LENGTH:
        await message.answer(f"Длина описания не должна превышать максимально допустимое значение.",
                             reply_markup=get_cancel_reply_keyboard())
        return
    name = (await state.get_data()).get('name')
    try:
        await Template.create(session=session, name=name, description=description,
                              formated_description=copy_text_message(description, message.entities),
                              creator_id=message.from_user.id)
        await state.clear()
        await message.answer(text="Шаблон успешно создан")
        await message.answer(text=LEXICON["ADMIN"]["main"], reply_markup=get_admin_panel_menu_kb())
    except Exception as e:
        await message.answer(f"При создании шаблона что-то пошло не так. {e}")
        await message.answer(text=LEXICON["ADMIN"]["main"], reply_markup=get_admin_panel_menu_kb())
    finally:
        await state.clear()


@router.message(TemplateAddStates.template_description)
async def handle_wrong_template_description(message: Message):
    await message.answer("Описание должно быть в текстовом формате", reply_markup=get_cancel_reply_keyboard())



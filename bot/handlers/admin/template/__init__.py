__all__ = ["router"]

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.lexicon import LEXICON
from database import DBHelper
from database.models import Template
from bot.filters import IsAdmin
from bot.keyboards import AdminPanelOptions
from bot.keyboards.admin_keyboards import get_admin_panel_template_menu_kb, get_templates_inline_kb
from .add import router as template_add_router, TemplateAddStates
from .edit import router as template_edit_router, TemplateEditStates

router = Router()
router.include_routers(
    template_add_router,
    template_edit_router
)


@router.message(F.text == AdminPanelOptions.template, IsAdmin())
async def handle_admin_template_command(message: Message):
    await message.answer(text=LEXICON["ADMIN"]["TEMPLATE"]["main"],
                         reply_markup=get_admin_panel_template_menu_kb())


@router.message(Command('cancel'), StateFilter(TemplateAddStates))
@router.message(F.text == "Отмена", StateFilter(TemplateAddStates))
async def handle_cancel_add_template(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Создание шаблона отменено", reply_markup=get_admin_panel_template_menu_kb())


@router.message(StateFilter(
    TemplateEditStates.template_description,
    TemplateEditStates.template_name,
), Command("cancel"))
@router.message(StateFilter(
    TemplateEditStates.template_description,
    TemplateEditStates.template_name,
), F.text == "Отмена")
@DBHelper.get_session
async def handle_cancel_edit_template_command(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    templates = await Template.all(session=session, order_by=Template.created_at)
    await message.answer("Редактирование шаблона отменено", reply_markup=ReplyKeyboardRemove())
    await message.answer(
        text="Выберите шаблон для редактирования",
        reply_markup=get_templates_inline_kb(templates),
    )


@router.callback_query(F.data == "back_to_templates_menu")
async def handle_back_button(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(text=LEXICON["ADMIN"]["TEMPLATE"]["main"],
                         reply_markup=get_admin_panel_template_menu_kb())
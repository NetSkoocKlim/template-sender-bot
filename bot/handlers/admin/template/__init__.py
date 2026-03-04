__all__ = ["router"]

from aiogram import F, Router, html
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.lexicon import LEXICON
from redis.asyncio import Redis
from database.models import Template, User
from bot.keyboards import AdminPanelOptions
from bot.keyboards.admin_keyboards import get_admin_panel_template_menu_kb, get_template_edit_inline_kb, \
    AdminPanelTemplateOptions
from .add import router as template_add_router
from .edit import router as template_edit_router
from bot.states.states import TemplateEditStates, TemplateAddStates

router = Router()
router.include_routers(
    template_add_router,
    template_edit_router
)


@router.callback_query(F.data == AdminPanelOptions.template)
@router.callback_query(F.data == "back_to_templates_menu")
async def handle_admin_template_command(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(text=LEXICON["ADMIN"]["TEMPLATE"]["main"],
                         reply_markup=get_admin_panel_template_menu_kb())


@router.callback_query(F.data == "cancel_button", StateFilter(TemplateAddStates))
async def handle_cancel_add_template(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Создание шаблона отменено")
    await callback.message.edit_text(LEXICON["ADMIN"]["TEMPLATE"]["main"], reply_markup=get_admin_panel_template_menu_kb())


@router.callback_query(StateFilter(
    TemplateEditStates.template_description,
    TemplateEditStates.template_name,
), F.data == "cancel_button")
async def handle_cancel_edit_template_command(callback: CallbackQuery, state: FSMContext,
                                              session: AsyncSession):
    template_data = (await state.get_data())
    template_id, template_index, template_is_chosen = (
        template_data["template_id"],
        template_data["template_index"],
        template_data["template_is_chosen"]
    )
    await state.clear()
    template = await Template.get(session=session, primary_key=template_id)
    await callback.answer("Редактирование шаблона отменено")
    template_info = html.bold(html.italic("✅ Выбран для рассылки ✅\n\n")) if template_is_chosen else ""
    template_info = template_info + LEXICON["ADMIN"]["TEMPLATE"]['template_info'].format(
        template_index,
        template.name,
        template.formated_description
    )
    await callback.message.answer(
        text=template_info,
        reply_markup=get_template_edit_inline_kb(template, template_index),
    )


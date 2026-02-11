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
from bot.keyboards.admin_keyboards import get_admin_panel_template_menu_kb, get_templates_inline_kb, \
    get_template_edit_inline_kb
from .add import router as template_add_router
from .edit import router as template_edit_router
from bot.states.states import TemplateEditStates, TemplateAddStates
from database.redis.redis_keys import admin_chosen_mailing_template_key

router = Router()
router.include_routers(
    template_add_router,
    template_edit_router
)


@router.message(F.text == AdminPanelOptions.template)
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
async def handle_cancel_edit_template_command(message: Message, state: FSMContext,
                                              session: AsyncSession, admin: User,
                                              redis: Redis):
    template_data = (await state.get_data())
    template_id, template_index, template_is_chosen = (
        template_data["template_id"],
        template_data["template_index"],
        template_data["template_is_chosen"]
    )
    await state.clear()
    template = await Template.get(session=session, primary_key=template_id)
    await message.answer("Редактирование шаблона отменено", reply_markup=ReplyKeyboardRemove())
    template_info = html.bold(html.italic("✅ Выбран для рассылки ✅\n\n")) if template_is_chosen else ""
    template_info = template_info + LEXICON["ADMIN"]["TEMPLATE"]['template_info'].format(
        template_index,
        template.name,
        template.formated_description
    )
    await message.answer(
        text=template_info,
        reply_markup=get_template_edit_inline_kb(template, template_is_chosen, template_index),
    )


@router.callback_query(F.data == "back_to_templates_menu")
async def handle_back_button(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(text=LEXICON["ADMIN"]["TEMPLATE"]["main"],
                         reply_markup=get_admin_panel_template_menu_kb())
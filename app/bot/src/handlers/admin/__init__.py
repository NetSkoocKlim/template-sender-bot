__all__ = ["router"]

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, CallbackQuery

from app.bot.src.filters import IsAdmin
from app.bot.src.keyboards.admin.constants import AdminPanelOptions
from app.bot.src.keyboards.admin.menu import get_admin_panel_menu_kb
from .template import router as template_router
from .receivers import router as receivers_router
from .mailing import router as mailing_router
from .statistic import router as statistic_router
from app.bot.src.lexicon import LEXICON

router = Router(name=__name__)
router.include_routers(
    template_router,
    receivers_router,
    mailing_router,
    statistic_router
)

router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

@router.message(Command("admin"))
@router.message(F.text == "Панель администратора", default_state)
async def handle_admin_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(text=LEXICON["ADMIN"]["main"],
                         reply_markup=get_admin_panel_menu_kb())

@router.callback_query(F.data == AdminPanelOptions.back.name, default_state)
async def handle_admin_command(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(text=LEXICON["ADMIN"]["main"],
                         reply_markup=get_admin_panel_menu_kb())



__all__ = ["router"]

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message

from bot.filters import IsAdmin
from bot.keyboards.admin_keyboards import get_admin_panel_menu_kb, AdminPanelOptions
from .template import router as template_router
from .receivers import router as receivers_router
from bot.lexicon import LEXICON
from bot.middelwares.database_middleware import database_middleware

router = Router(name=__name__)
router.include_routers(
    template_router,
    receivers_router,
)

router.message.outer_middleware(database_middleware)
router.message.filter(IsAdmin())
router.callback_query.outer_middleware(database_middleware)
router.callback_query.filter(IsAdmin())

@router.message(Command("admin"))
@router.message(F.text == "Панель администратора", default_state)
@router.message(F.text == AdminPanelOptions.back, default_state)
async def handle_admin_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(text=LEXICON["ADMIN"]["main"],
                         reply_markup=get_admin_panel_menu_kb())



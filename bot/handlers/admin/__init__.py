__all__ = ["router"]

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message

from bot.filters import IsAdmin
from bot.keyboards.admin_keyboards import get_admin_panel_menu_kb
from .template import router as template_router
from bot.lexicon import LEXICON

router = Router(name=__name__)
router.include_router(template_router)


@router.message(Command("admin"), IsAdmin())
@router.message(F.text == "Панель администратора", default_state, IsAdmin())
@router.message(F.text == "Вернуться к панели администратора", default_state, IsAdmin())
async def handle_admin_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(text=LEXICON["ADMIN"]["main"],
                         reply_markup=get_admin_panel_menu_kb())



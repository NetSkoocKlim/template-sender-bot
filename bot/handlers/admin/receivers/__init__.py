__all__ = ["router"]

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery


from bot.keyboards import AdminPanelOptions
from bot.keyboards.admin_keyboards import get_admin_panel_receiver_menu_kb, AdminPanelReceiverOptions, \
    get_receivers_list_kb
from bot.lexicon import LEXICON
from database.models import User
from database.redis import redis
from .add import router as receiver_add_router

router = Router()
router.include_routers(
    receiver_add_router,
)

@router.message(F.text == AdminPanelOptions.user_list)
async def handle_admin_receiver_menu(message: Message):
    await message.answer(text=LEXICON["ADMIN"]["RECEIVER"]["main"],
                         reply_markup=get_admin_panel_receiver_menu_kb())


@router.message(F.text == AdminPanelReceiverOptions.view)
async def handle_receiver_view_button(message: Message, admin: User):
    redis_key = f"admin:{admin.id}:receivers"
    saved_users = await redis.get(redis_key)
    if not saved_users:
        await message.answer(text="Вы ещё не сохранили ни одного пользователя")
        await message.answer(text=LEXICON["ADMIN"]["RECEIVER"]["main"],
                             reply_markup=get_admin_panel_receiver_menu_kb())
        return

    await message.answer(text=LEXICON["ADMIN"]["RECEIVER"]["view_list"],
                         reply_markup=get_receivers_list_kb(saved_users))


@router.message(F.text == AdminPanelReceiverOptions.clear)
async def handle_receiver_clear(message: Message, admin: User):
    redis_key = f"admin:{admin.id}:receivers"
    await redis.set(redis_key, '')
    await message.answer("Список был полностью очищен")
    await message.answer(text=LEXICON["ADMIN"]["RECEIVER"]["main"],
                         reply_markup=get_admin_panel_receiver_menu_kb())


@router.callback_query(F.data == "back_to_receivers_menu")
async def handle_receiver_callback_query(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(text=LEXICON["ADMIN"]["RECEIVER"]["main"],
                         reply_markup=get_admin_panel_receiver_menu_kb())
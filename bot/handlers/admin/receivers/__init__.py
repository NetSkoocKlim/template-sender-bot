__all__ = ["router"]

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import AdminPanelOptions
from bot.keyboards.admin_keyboards import get_admin_panel_receiver_menu_kb, AdminPanelReceiverOptions, \
    get_receivers_list_kb, ReceiverData
from bot.lexicon import LEXICON
from bot.states.states import ReceiverMenuStates
from bot.utils.change_user_list import get_changed_user_list
from database.models import User
from .add import router as receiver_add_router
from .delete import router as receiver_delete_router
from database.redis.redis_keys import admin_receivers_key

router = Router()
router.include_routers(
    receiver_add_router,
    receiver_delete_router
)

@router.callback_query(F.data == AdminPanelOptions.user_list)
async def handle_admin_receiver_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(text=LEXICON["ADMIN"]["RECEIVER"]["main"],
                         reply_markup=get_admin_panel_receiver_menu_kb())


@router.callback_query(F.data == AdminPanelReceiverOptions.view)
async def handle_receiver_view_button(callback: CallbackQuery,
                                      admin: User,
                                      session: AsyncSession,
                                      redis: Redis):
    saved_users = await redis.get(admin_receivers_key(admin.id))
    if not saved_users:
        await callback.answer(text="Вы ещё не сохранили ни одного пользователя")
        return
    await User.get_ids_by_usernames(session, saved_users)
    await callback.message.edit_text(text=LEXICON["ADMIN"]["RECEIVER"]["view_list"],
                         reply_markup=get_receivers_list_kb(saved_users))


@router.callback_query(ReceiverData.filter())
async def handle_receiver_delete(callback: CallbackQuery, callback_data: ReceiverData,
                                 admin: User, redis: Redis):
    user_name_to_delete = callback_data.username
    saved_users = await redis.get(admin_receivers_key(admin.id))
    changed_count, new_users = get_changed_user_list(saved_users, [user_name_to_delete], False)
    try:
        await redis.set(admin_receivers_key(admin.id), new_users)

        if new_users == '':
            await callback.message.edit_text(text=LEXICON["ADMIN"]["RECEIVER"]["main"],
                                             reply_markup=get_admin_panel_receiver_menu_kb())
        else:
            await callback.message.edit_text(text=LEXICON["ADMIN"]["RECEIVER"]["view_list"],
                                             reply_markup=get_receivers_list_kb(new_users))
        await callback.answer("Юзер успешно удалён")
    except Exception as e:
        await callback.message.edit_text(text=LEXICON["ADMIN"]["RECEIVER"]["main"],
                             reply_markup=get_admin_panel_receiver_menu_kb())
        await callback.answer(f"При удалении юзера произошла ошибка, {e}")


@router.callback_query(F.data == AdminPanelReceiverOptions.clear)
async def handle_receiver_clear(callback: CallbackQuery, admin: User, redis: Redis):
    await redis.set(admin_receivers_key(admin.id), '')
    await callback.answer("Список был полностью очищен")

@router.callback_query(F.data == "cancel_button", StateFilter(ReceiverMenuStates))
async def handle_cancel_add_template(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(text=LEXICON["ADMIN"]["RECEIVER"]["main"],
                                  reply_markup=get_admin_panel_receiver_menu_kb())

@router.callback_query(F.data == "back_to_receivers_menu")
async def handle_receiver_callback_query(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(text=LEXICON["ADMIN"]["RECEIVER"]["main"],
                         reply_markup=get_admin_panel_receiver_menu_kb())
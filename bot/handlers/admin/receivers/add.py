from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from redis.asyncio import Redis
from database.redis.redis_keys import admin_receivers_key

from bot.states.states import ReceiverMenuStates
from bot.keyboards.admin_keyboards import AdminPanelReceiverOptions, get_admin_panel_receiver_menu_kb
from bot.keyboards.common import get_cancel_button
from bot.lexicon import LEXICON
from bot.utils.change_user_list import get_changed_user_list
from database.models import User

router = Router()


@router.callback_query(F.data == AdminPanelReceiverOptions.expand)
async def handle_admin_receiver_expansion_button(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReceiverMenuStates.add_receivers)
    await state.update_data(callback_id=callback.id,
                            callback_message_id=callback.message.message_id)
    await callback.message.edit_text(text=LEXICON["ADMIN"]["RECEIVER"]["expand_list"],
                         reply_markup=get_cancel_button())

@router.message(StateFilter(ReceiverMenuStates.add_receivers), F.text)
async def handle_admin_receiver_expansion(message: Message, state: FSMContext, admin: User, redis: Redis):
    saved_users = await redis.get(admin_receivers_key(admin.id))
    users_to_save = message.text.split()
    added_count, new_users = get_changed_user_list(saved_users, users_to_save)
    result_message = LEXICON["ADMIN"]["RECEIVER"]["expand_result"].format(added_count)
    callback_data = await state.get_data()
    callback_id, callback_message_id = callback_data.get('callback_id'), callback_data.get('callback_message_id')
    if added_count == 0:
        result_message = "Не было добавлено ни одного нового пользователя"
    try:
        await redis.set(admin_receivers_key(admin.id), new_users)
        await message.bot.edit_message_text(
            text=LEXICON["ADMIN"]["RECEIVER"]["main"],
            chat_id=message.chat.id,
            message_id=callback_message_id,
            reply_markup=get_admin_panel_receiver_menu_kb()
        )
        await message.delete()
        await message.bot.answer_callback_query(
            callback_id,
            text=result_message
        )
    except Exception as e:
        await message.bot.answer_callback_query(
            callback_id,
            text=str(e)
        )
    finally:
        await state.clear()

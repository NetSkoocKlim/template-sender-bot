import asyncio

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states.states import ReceiverMenuStates
from bot.keyboards.admin_keyboards import AdminPanelReceiverOptions, get_admin_panel_receiver_menu_kb
from bot.keyboards.common import get_cancel_reply_keyboard
from bot.lexicon import LEXICON
from bot.utils.change_user_list import get_changed_user_list
from redis.asyncio import Redis
from database.redis.redis_keys import admin_receivers_key
from database.models import User

router = Router()


@router.message(F.text == AdminPanelReceiverOptions.delete)
async def handle_admin_receiver_expansion_button(message: Message, state: FSMContext):
    await state.set_state(ReceiverMenuStates.delete_receivers)
    await message.answer(text=LEXICON["ADMIN"]["RECEIVER"]["delete_list"],
                         reply_markup=get_cancel_reply_keyboard())


@router.message(StateFilter(ReceiverMenuStates.delete_receivers), F.text)
async def handle_admin_receiver_expansion(message: Message, state: FSMContext, admin: User,
                                          redis: Redis):
    saved_users = await redis.get(admin_receivers_key(admin.id))
    users_to_delete = message.text.split()
    deleted_count, new_users = get_changed_user_list(saved_users, users_to_delete, False)
    result_message = LEXICON["ADMIN"]["RECEIVER"]["delete_result"].format(deleted_count)
    if deleted_count == 0:
        result_message = ("Ни один из указанных пользователей не был удалён: \n "
                          "либо указанные юзернеймы не были в списке, либо"
                          " они были написаны в неправильном формате")
    try:
        await redis.set(admin_receivers_key(admin.id), new_users)
        await message.answer(text=result_message)
        await message.answer(text=LEXICON["ADMIN"]["RECEIVER"]["main"],
                             reply_markup=get_admin_panel_receiver_menu_kb())
    except Exception as e:
        await message.answer(text=str(e))
    finally:
        await state.clear()

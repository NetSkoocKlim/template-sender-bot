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
from database import redis
from database.models import User

router = Router()


@router.message(F.text == AdminPanelReceiverOptions.expand)
async def handle_admin_receiver_expansion_button(message: Message, state: FSMContext):
    await state.set_state(ReceiverMenuStates.add_receivers)
    await message.answer(text=LEXICON["ADMIN"]["RECEIVER"]["expand_list"],
                         reply_markup=get_cancel_reply_keyboard())

@router.message(StateFilter(ReceiverMenuStates.add_receivers), F.text)
async def handle_admin_receiver_expansion(message: Message, state: FSMContext, admin: User):
    saved_users = (await redis.get(f"admin:{admin.id}:receivers"))
    if not saved_users:
        saved_users = set()
    else:
        saved_users = set(saved_users.split())

    users_to_save = message.text.split()
    new_saved_count = 0
    for username in users_to_save:
        username_length = len(username)
        if 5 <= username_length <= 32 and username[0] == '@' and not username in saved_users:
            new_saved_count += 1
            saved_users.add(username)

    result_message = LEXICON["ADMIN"]["RECEIVER"]["expand_result"].format(new_saved_count)
    updated_users = " ".join(saved_users)
    if new_saved_count == 0:
        result_message = ("Не было добавлено ни одного нового пользователя: \n "
                          "либо указанные пользователи уже были сохранены, либо"
                          " были написаны в неправильном формате")
    try:
        await redis.set(f"admin:{admin.id}:receivers", updated_users)
        await message.answer(text=result_message)
        await message.answer(text=LEXICON["ADMIN"]["RECEIVER"]["main"],
                             reply_markup=get_admin_panel_receiver_menu_kb())
    except Exception as e:
        await message.answer(text=str(e))
    finally:
        await state.clear()

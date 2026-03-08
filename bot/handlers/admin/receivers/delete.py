from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.states.states import ReceiverMenuStates
from bot.keyboards.admin_keyboards import AdminPanelReceiverOptions
from bot.keyboards.common import get_cancel_button
from bot.lexicon import LEXICON
router = Router()

@router.callback_query(F.data == AdminPanelReceiverOptions.delete)
async def handle_admin_receiver_expansion_button(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReceiverMenuStates.delete_receivers)
    await state.update_data(message_id=callback.message.message_id)
    await callback.message.edit_text(text=LEXICON["ADMIN"]["RECEIVER"]["delete_list"],
                         reply_markup=get_cancel_button())


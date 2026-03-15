from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.states.states import ReceiverMenuStates
from bot.keyboards.admin.constants import AdminPanelReceiverOptions
from bot.keyboards.common import get_cancel_button
from bot.lexicon import LEXICON

router = Router()


@router.callback_query(F.data == AdminPanelReceiverOptions.expand_rcvr.name)
async def handle_admin_receiver_expansion_button(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReceiverMenuStates.add_receivers)
    await state.update_data(message_id=callback.message.message_id)
    await callback.message.edit_text(text=LEXICON["ADMIN"]["RECEIVER"]["expand_list"],
                         reply_markup=get_cancel_button())

from aiogram import Router, F
from aiogram.types import Message

router = Router(name=__name__)

# @router.message(F)
# async def handle_any_message(message: Message):
#
#     await message.answer()
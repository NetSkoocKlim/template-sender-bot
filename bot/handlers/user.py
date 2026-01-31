from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from config import settings
from database.models import User
from database import DBHelper

router = Router(name=__name__)


@router.message(CommandStart())
@DBHelper.get_session
async def proceed_start_command(message: Message, session: AsyncSession):
    await User.create_or_update(session, id=message.from_user.id, username=message.from_user.username)
    await message.answer(text='Добро пожаловать!')


@router.message(F.text == settings.secret)
@DBHelper.get_session
async def proceed_secret_command(message: Message, session: AsyncSession):
    user: User = await User.get(session, primary_key=message.from_user.id)
    if not user.is_admin:
        setattr(user, "is_admin", True)
        await message.answer(text='Вы получили доступ к админ-панели.\n'
                                  'Чтобы перейти к ней нажмите на кнопку ниже.\n'
                                  'Для перехода к ней в дальнейшем необходимо будет использовать /admin',
                             reply_markup=ReplyKeyboardMarkup(keyboard=[
                                 [KeyboardButton(text="Панель администратора")]
                             ], resize_keyboard=True))

        await message.delete()


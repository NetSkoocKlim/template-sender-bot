from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from config import settings
from shared.src.database.models import User
from shared.src.database import DBHelper

router = Router(name=__name__)


@router.message(CommandStart())
@DBHelper.get_session
async def proceed_start_command(message: Message, session: AsyncSession):
    await message.answer(text='Добро пожаловать!')


@router.message(F.text == settings.bot.admin_secret)
@DBHelper.get_session
async def proceed_secret_command(message: Message, session: AsyncSession):
    user: User = await User.get(session, primary_key=message.from_user.id)
    if not user.is_admin:
        setattr(user, "is_admin", True)
        await message.answer(text='Вы получили доступ к админ-панели.\n'
                                  'Чтобы перейти используйте команду /admin\n')
    else:
        await message.answer(text='Вы уже являйтесь администратором.\n'
                                  'Чтобы перейти к админ-панели используйте команду /admin\n')

    await message.delete()

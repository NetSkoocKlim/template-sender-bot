__all__ = ["router"]
import io

from aiogram import Router, F, html
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import AdminPanelOptions
from bot.keyboards.admin_keyboards import get_admin_panel_receiver_menu_kb, AdminPanelReceiverOptions, \
    get_receivers_list_kb
from bot.lexicon import LEXICON
from bot.states.states import ReceiverMenuStates
from database.models import User, Receiver
from .add import router as receiver_add_router
from .delete import router as receiver_delete_router

router = Router()
router.include_routers(
    receiver_add_router,
    receiver_delete_router
)

MAX_RECEIVERS_COUNT = 400
MAX_FILE_SIZE = 1 * 1024 * 1024
MAX_RECEIVERS_TO_SHOW = 20

@router.callback_query(F.data == AdminPanelOptions.user_list)
async def handle_admin_receiver_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(text=LEXICON["ADMIN"]["RECEIVER"]["main"],
                         reply_markup=get_admin_panel_receiver_menu_kb())


@router.callback_query(F.data == AdminPanelReceiverOptions.view)
async def handle_receiver_view_button(callback: CallbackQuery,
                                      admin: User,
                                      session: AsyncSession,
                                      redis: Redis,
                                      state: FSMContext):
    saved_count = await Receiver.count_total(
        session=session,
        filter_by={
            "admin_id": admin.id,
        }
    )
    if saved_count == 0:
        await callback.answer(text="Вы ещё не сохранили ни одного пользователя")
        return
    saved_users: list[Receiver] = await Receiver.all(
        session=session,
        order_by=Receiver.username,
        limit=MAX_RECEIVERS_TO_SHOW
    )
    saved_users_str = '\n'.join(user.username for user in saved_users)
    if saved_count > MAX_RECEIVERS_TO_SHOW:
        additional_text = "\nи ещё " + html.underline(str(saved_count - MAX_RECEIVERS_TO_SHOW))
        saved_users_str += additional_text
    await callback.message.edit_text(
        text=LEXICON["ADMIN"]["RECEIVER"]["view_list"].format(saved_count, saved_users_str),
        reply_markup=get_receivers_list_kb(True)
    )

@router.callback_query(F.data == "download_receivers_list")
async def handle_download_receivers_list(
        callback: CallbackQuery,
        session: AsyncSession,
        state: FSMContext
):
    saved_users = await Receiver.all(
        session=session,
        order_by=Receiver.username,
    )
    await callback.answer()
    with io.BytesIO() as buf:
        for user in saved_users:
            line = f"{user.username}\n".encode("utf-8")
            buf.write(line)

        await callback.bot.send_document(
            chat_id=callback.message.chat.id,
            document=BufferedInputFile(
                buf.getvalue(),
                filename="receivers.txt"
            ),
        )

@router.callback_query(F.data == "back_to_receivers_menu")
async def handle_receiver_callback_query(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(text=LEXICON["ADMIN"]["RECEIVER"]["main"],
                         reply_markup=get_admin_panel_receiver_menu_kb())


@router.callback_query(F.data == AdminPanelReceiverOptions.clear)
async def handle_receiver_clear(callback: CallbackQuery, admin: User, session: AsyncSession):
    await Receiver.delete_all_by_filter(
        session=session,
        admin_id=admin.id,
    )
    await callback.answer("Список был полностью очищен")

@router.callback_query(F.data == "cancel_button", StateFilter(ReceiverMenuStates))
async def handle_cancel_changing_receiver_list(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(text=LEXICON["ADMIN"]["RECEIVER"]["main"],
                                  reply_markup=get_admin_panel_receiver_menu_kb())


@router.message(StateFilter(ReceiverMenuStates.add_receivers), F.text)
@router.message(StateFilter(ReceiverMenuStates.add_receivers), F.document)
@router.message(StateFilter(ReceiverMenuStates.delete_receivers), F.text)
@router.message(StateFilter(ReceiverMenuStates.delete_receivers), F.document)
async def handle_receiver_list_change(message: Message, state: FSMContext, admin: User,
                                          session: AsyncSession):
    if message.document is None:
        input_users = message.text.split()
    else:
        document = message.document
        if document.file_size > MAX_FILE_SIZE:
            return await message.answer(
                f"Файл слишком большой! Максимальный размер: {MAX_FILE_SIZE // 1024} КБ."
            )
        if not document.file_name.endswith(".txt"):
            return await message.answer("Тип отправляемого файла должен быть .txt")
        file_bytes = await message.bot.download(message.document.file_id)
        content = file_bytes.read(500_000).decode('utf-8', errors='ignore')
        input_users = content.split()

    def _validate_usernames():
        usernames = []
        for username in input_users:
            username = username.strip()
            username_length = len(username)
            if 6 <= username_length <= 33 and username[0] == '@':
                usernames.append(username)
        return list(set(usernames))
    validated_usernames = _validate_usernames()

    current_state = await state.get_state()
    if current_state == ReceiverMenuStates.add_receivers:
        saved_count = await Receiver.count_total(
            session=session,
            filter_by={
                "admin_id": admin.id,
            }
        )
        validated_usernames = validated_usernames[:max(MAX_RECEIVERS_COUNT - saved_count, 0)]
        added_users_count = await Receiver.add_receivers(
            session=session,
            admin_id=admin.id,
            usernames=validated_usernames
        )

        if added_users_count == 0:
            result_message = "Не было добавлено ни одного нового пользователя"
        else:
            result_message = LEXICON["ADMIN"]["RECEIVER"]["expand_result"].format(added_users_count)
    else:
        deleted_count = await Receiver.delete_receivers(
            session=session,
            usernames=_validate_usernames(),
            admin_id=admin.id
        )
        if deleted_count == 0:
            result_message = "Ни один из указанных пользователей не был удалён"
        else:
            result_message = LEXICON["ADMIN"]["RECEIVER"]["delete_result"].format(deleted_count)

    state_data = await state.get_data()
    message_id = state_data['message_id']
    try:
        await message.bot.send_message(
            text=result_message,
            chat_id=admin.id,
        )
        await message.bot.send_message(
            text=LEXICON["ADMIN"]["RECEIVER"]["main"],
            chat_id=message.chat.id,
            reply_markup=get_admin_panel_receiver_menu_kb()
        )
        await message.delete()
        await message.bot.delete_message(
            chat_id=message.chat.id,
            message_id=message_id
        )
    except Exception as e:
        pass
    finally:
        await state.clear()

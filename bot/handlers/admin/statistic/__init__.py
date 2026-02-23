import email
import os
import re
import urllib.parse
from io import BytesIO
from email.message import EmailMessage
# from cgi import parse_header
import aiohttp
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InputFile, BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import AdminPanelOptions
from bot.keyboards.admin_keyboards import get_admin_panel_statistic_kb, DownloadMailingData, AdminPanelStatisticOptions
from bot.lexicon import LEXICON
from database.models import User, Mailing

router = Router()

@router.callback_query(F.data == AdminPanelOptions.statistic)
async def statistic_menu_handler(callback: CallbackQuery,
                                 session: AsyncSession,
                                 admin: User):
    last_mailing: Mailing = await Mailing.get_newest(
        session,
        filter_by={
            "admin_id": admin.id,
        }
    )
    if not last_mailing:
        await callback.answer("Вы ещё не совершали рассылку")
        return

    await callback.answer()
    await callback.message.edit_text(
        text=LEXICON["ADMIN"]["STATISTIC"]["main"],
        reply_markup=get_admin_panel_statistic_kb(last_mailing.csv_result_key)
    )

def parse_content_disposition(cd_header: str) -> str | None:
    """
    Возвращает безопасное имя файла из заголовка Content-Disposition или None.
    Поддерживает filename* (RFC5987) и обычный filename, а также RFC2047.
    """
    if not cd_header:
        return None
    m = re.search(r'filename\s*=\s*(?P<val>(".*?"|\'.*?\'|[^;]+))', cd_header, flags=re.IGNORECASE)
    if m:
        val = m.group("val").strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        filename = val

        return os.path.basename(filename)
    return None

@router.callback_query(DownloadMailingData.filter())
async def handle_download_last_mailing(
        callback: CallbackQuery,
        callback_data: DownloadMailingData,
):
    mailing_key = callback_data.key
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url=f"http://127.0.0.1:8004/download/{mailing_key}"
        ) as resp:
            data = await resp.read()
            cd = resp.headers.get('Content-Disposition', '')
            filename = parse_content_disposition(cd) or f"mailing-{mailing_key}.csv"
            input_file = BufferedInputFile(data, filename=filename)
            await callback.message.answer_document(document=input_file)
    await callback.answer()


@router.callback_query(AdminPanelStatisticOptions.view)
async def handle_view_statistic_button(
        callback: CallbackQuery,
        admin: User,
        session: AsyncSession,
):

    mailings, back_anchor, forward_anchor = await Mailing.paginate_fast(
        session,
        page=1
    )



from typing import Literal

from aiogram.filters.callback_data import CallbackData
from .constants import TemplateEditAction

class TemplateEditData(CallbackData, prefix="edit_tmplt"):
    action: TemplateEditAction
    id: int
    index: int | None = None
    creator_id: int
    name: str
    is_chosen: bool = False

class PaginateButtonData(CallbackData, prefix="pgnt"):
    model: str
    anchor: str
    forward: bool = True

class DownloadMailingData(CallbackData, prefix="download_data"):
    key: str

class MailingViewData(CallbackData, prefix="view_data"):
    id: int

    sender_id: int | None = None
    mailing_date: str | None = None

class MailingTemplateViewData(CallbackData, prefix="view_mailing_template"):
    action: Literal["view", "back"]

    id: int
    mailing_id: int
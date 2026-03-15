from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from .fabrics import PaginateButtonData

def add_pagination_footer(
    builder: InlineKeyboardBuilder,
    page: int,
    page_count: int,
    model_name: str,
    forward_anchor: str | None,
    backward_anchor: str | None,
    back_callback: str
) -> InlineKeyboardBuilder:
    if not backward_anchor:
        backward_button = InlineKeyboardButton(text="#", callback_data="empty_pagination")
    else:
        backward_button = InlineKeyboardButton(
            text="<",
            callback_data=PaginateButtonData(
                anchor=backward_anchor,
                forward=False,
                model=model_name
            ).pack()
        )

    if not forward_anchor:
        forward_button = InlineKeyboardButton(text="#", callback_data="empty_pagination")
    else:
        forward_button = InlineKeyboardButton(
            text=">",
            callback_data=PaginateButtonData(
                anchor=forward_anchor,
                forward=True,
                model=model_name
            ).pack()
        )

    page_button = InlineKeyboardButton(
        text=f"{page}/{page_count}",
        callback_data="empty_pagination"
    )

    builder.row(backward_button, page_button, forward_button)

    builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data=back_callback,
        )
    )

    return builder
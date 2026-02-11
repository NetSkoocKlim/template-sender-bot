from enum import Enum
from typing import Union


class ChangeMode(Enum):
    ADD = "add"
    DELETE = "delete"


def get_changed_user_list(saved_users: str | None, users_to_change: list[str], is_add: bool = True) -> tuple[int, str] :
    new_users = set(saved_users.split() if saved_users else [])
    changed_count = 0
    for username in users_to_change:
        username_length = len(username)
        if 6 <= username_length <= 33 and username[0] == '@':
            if is_add and not username in new_users:
                changed_count += 1
                new_users.add(username)
            elif not is_add and username in new_users:
                changed_count += 1
                new_users.remove(username)

    return changed_count, " ".join(new_users)

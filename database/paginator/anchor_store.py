import json
import secrets
from typing import Optional
from ..redis import get_redis

ANCHOR_TTL = 60 * 3
ANCHOR_STATE_TTL = 60 * 60


async def store_payload_with_token(payload: str, admin_id: int, ttl: int = ANCHOR_TTL) -> str:
    r = get_redis()
    token = secrets.token_urlsafe(12)
    key = f"admin:{admin_id}:anchor:short:{token}"
    await r.set(key, payload, ex=ttl)
    return token

async def retrieve_payload_by_token(token: str, admin_id: int) -> Optional[str]:
    r = get_redis()
    key = f"admin:{admin_id}:anchor:short:{token}"
    return await r.get(key)


async def store_page_anchor_state(admin_id: int, anchor: str, forward: bool, current_page: int, ttl: int = ANCHOR_STATE_TTL):
    r = get_redis()
    key = f"admin:{admin_id}:anchor:current_page"
    payload = {
        "anchor": anchor,
        "forward": forward,
        "current_page": current_page
    }
    await r.set(key, json.dumps(payload), ex=3600)


async def get_page_anchor_state(admin_id: int, ) -> tuple[str | None, bool, int] | None:
    r = get_redis()
    if r is None:
        return None, True, 1
    key = f"admin:{admin_id}:anchor:current_page"
    raw = await r.get(key)
    if not raw:
        return None, True, 1
    try:
        data = json.loads(raw)
        return (data.get("anchor", None),
                bool(data.get("forward", True)),
                int(data.get("current_page", 1)))
    except Exception:
        return None, True, 1

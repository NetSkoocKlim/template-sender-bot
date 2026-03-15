import json
import logging
import secrets
from typing import Optional
from ..redis import get_redis

ANCHOR_TTL = 60 * 3
ANCHOR_STATE_TTL = 60 * 60
logger = logging.getLogger(__name__)

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
    logger.info(f"Storing page anchor state into redis: "
                f"anchor: {anchor}, forward: {forward}, current_page: {current_page}")
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
    try:
        data = json.loads(raw)
        anchor = data.get("anchor", None)
        forward = bool(data.get("forward", True))
        current_page = int(data.get("current_page", 1))
    except Exception as e:
        logger.error(f"Failed to get page anchor state: {e}")
        anchor = None
        forward = True
        current_page = 1
    logger.info(f"Received page anchor state from redis: "
                f"anchor: {anchor}, forward: {forward}, current_page: {current_page}")
    return anchor, forward, current_page
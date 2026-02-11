from typing import Optional
from redis.asyncio import Redis
from config import settings
_redis: Optional[Redis] = None

async def init_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis(
            host=settings.redis.HOST,
            port=settings.redis.PORT,
            db=settings.redis.db,
            encoding='utf-8',
            decode_responses=True
        )
        await _redis.ping()
    return _redis

async def close_redis() -> None:
    global _redis
    if _redis is not None:
        try:
            await _redis.close()
        finally:
            _redis = None

def get_redis() -> Optional[Redis]:
    return _redis


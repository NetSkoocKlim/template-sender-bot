from redis.asyncio import Redis

from config import settings

redis = Redis(
    host=settings.redis.HOST,
    port=settings.redis.PORT,
    db=settings.redis.db,
    encoding='utf-8',
    decode_responses=True
)

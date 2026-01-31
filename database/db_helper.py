from functools import wraps

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from config import settings


class DBHelper:
    engine = create_async_engine(url=settings.db.URL, echo=False)
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


    @classmethod
    def get_session(cls, f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            async with cls.async_session() as session:
                async with session.begin():
                    kwargs["session"] = session
                    return await f(*args, **kwargs)

        return wrapper
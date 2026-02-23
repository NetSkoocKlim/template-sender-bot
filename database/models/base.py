import datetime
import typing as t
from dataclasses import dataclass

from sqlalchemy import Column, select, func, BigInteger, desc, TIMESTAMP
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, selectinload, DeclarativeBase, Mapped, mapped_column

T = t.TypeVar("T", bound="BaseModel")

@dataclass
class Anchor:
    page: int
    value: int

    def __init__(self, page: int = 1, value: int = 0):
        self.page = page
        self.value = value

    def __str__(self):
        return f"Anchor(page={self.page}, value={self.value})"

class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True
    _must_be_active = False

    _PAGE_SIZE = 2

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    def to_dict(self) -> t.Dict:
        """
        Convert the data to a dictionary.
        """
        return {f"{self.__tablename__}_{col.name}": getattr(self, col.name) for col in
                t.cast(t.List[Column], t.cast(object, self.__table__.columns))}

    @classmethod
    def get_page_size(cls) -> int:
        return cls._PAGE_SIZE

    @staticmethod
    def _get_column(
            model: t.Type[T],
            col: InstrumentedAttribute[t.Any],
    ) -> str:
        """Get the column name from InstrumentedAttribute or string, validating existence."""
        if isinstance(col, str):
            name = col
        else:
            # InstrumentedAttribute provides .key
            name = getattr(col, "key", None) or getattr(col, "name", None)
        if name not in model.__table__.columns:
            raise ValueError(f"Column {name} not found in {model.__name__}")
        return name

    @classmethod
    def _get_primary_key(cls) -> str:
        """Return the primary key of the model."""
        return list(cls.__table__.primary_key.columns)[0].name

    @classmethod
    def _get_select_statement(
            cls,
            select_value: t.Any = None,
            *,
            join_tables: t.Union[t.Any, t.List[t.Any]] = None,
            filters: t.Sequence[t.Any] = None,
            filter_by: dict[str, t.Any] = None,
            order_by: t.Union[Column, None] = None,
    ):
        if select_value is not None:
            statement = select(select_value)
        else:
            statement = select(cls)
        if cls._must_be_active:
            if not filter_by:
                filter_by = {"is_active": True}
            else:
                filter_by["is_active"] = True
        if join_tables is not None:
            if isinstance(join_tables, (list, tuple, set)):
                opts = [selectinload(rel) for rel in join_tables]
                statement = statement.options(*opts)
            else:
                statement = statement.options(selectinload(join_tables))
        if filter_by is not None:
            statement = statement.filter_by(**filter_by)
        if filters is not None:
            statement = statement.filter(*filters)
        if order_by is not None:
            statement = statement.order_by(order_by)

        return statement


    @classmethod
    async def create(
            cls: t.Type[T],
            session: AsyncSession,
            **kwargs,
    ) -> T:
        """Create a new record in the database."""
        instance = cls(**kwargs)
        session.add(instance)
        await session.flush()
        return instance

    @classmethod
    async def get(
            cls: t.Type[T],
            session: AsyncSession,
            primary_key: int,
    ) -> T:
        if cls._must_be_active:
            filter_by = {cls._get_primary_key(): primary_key}
            statement = cls._get_select_statement(filter_by=filter_by)
            return await session.scalar(statement)
        return await session.get(cls, primary_key)

    @classmethod
    async def get_with_join(
            cls: t.Type[T],
            session: AsyncSession,
            primary_key: int,
            join_tables: t.Union[t.Any, t.List[t.Any]] = None,
    ) -> T:
        """Get a record from the database by its primary key."""
        filter_by = {cls._get_primary_key(): primary_key}
        statement = cls._get_select_statement(join_tables=join_tables, filter_by=filter_by)
        result = await session.execute(statement)
        return result.scalars().first()

    @classmethod
    async def get_by_key(
            cls: t.Type[T],
            session: AsyncSession,
            key: InstrumentedAttribute[t.Any],
            value: t.Any,
    ) -> T | None:
        """Get a record by a key."""
        filter_by = {cls._get_column(cls, key): value}
        statement = cls._get_select_statement(filter_by=filter_by)
        result = await session.execute(statement)
        return result.scalars().first()

    @classmethod
    async def get_by_filter(
            cls: t.Type[T],
            session: AsyncSession,
            **kwargs,
    ) -> T | None:
        """Get a record from the database by a filters."""
        statement = cls._get_select_statement(filter_by=kwargs)
        result = await session.execute(statement)
        return result.scalars().first()

    @classmethod
    async def get_newest(
            cls,
            session: AsyncSession,
            filter_by: dict[str, t.Any]
    ):
        statement = cls._get_select_statement(filter_by=filter_by, order_by=cls.created_at.desc())
        statement = statement.limit(1)
        result = await session.execute(statement)
        return result.scalars().first()

    @classmethod
    async def update(
            cls: t.Type[T],
            session: AsyncSession,
            primary_key: int,
            **kwargs,
    ) -> t.Union[T, None]:
        """Update a record in the database."""
        instance = await cls.get(session, primary_key)
        if instance:
            for key, value in kwargs.items():
                setattr(instance, key, value)
            await session.flush()
            return instance
        return None

    @classmethod
    async def update_by_key(
            cls: t.Type[T],
            session: AsyncSession,
            key: InstrumentedAttribute[t.Any],
            value: t.Any,
            **kwargs,
    ) -> T:
        """Update a record in the database by a key."""
        
        instance = await cls.get_by_key(session, key, value)
        if instance:
            for attr, value in kwargs.items():
                setattr(instance, attr, value)
            session.add(instance)
            await session.flush()
        return instance

    @classmethod
    async def delete(
            cls: t.Type[T],
            session: AsyncSession,
            primary_key: int,
    ) -> T | None:
        
        instance = await cls.get(session, primary_key)
        if instance:
            await session.delete(instance)
            await session.flush()
        return instance

    @classmethod
    async def delete_by_key(
            cls: t.Type[T],
            session: AsyncSession,
            key: InstrumentedAttribute[t.Any],
            value: t.Any,
    ) -> T | None:
        """Delete a record from the database by a key."""
        
        instance = await cls.get_by_key(session, key, value)
        if instance:
            await session.delete(instance)
            await session.flush()
        return instance

    @classmethod
    async def delete_by_filter(
            cls: t.Type[T],
            session: AsyncSession,
            **kwargs,
    ) -> T | None:
        """Delete a record from the database by a filters."""
        
        instance = await cls.get_by_filter(session, **kwargs)
        if instance:
            await session.delete(instance)
            await session.flush()
        return instance

    @classmethod
    async def create_or_update(
            cls: t.Type[T],
            session: AsyncSession,
            **kwargs,
    ) -> T:
        """Get and update a record from the database by its primary key."""
        primary_key = kwargs.get(cls._get_primary_key())
        instance = await cls.get(session, primary_key) if primary_key else None
        if instance:
            await cls.update(session, primary_key, **kwargs)
            return instance
        return await cls.create(session, **kwargs)

    @classmethod
    async def exists(
            cls: t.Type[T],
            session: AsyncSession,
            primary_key: int,
    ) -> bool:
        """Check if a record exists in the database by its primary key."""

        return await session.get(cls, primary_key) is not None

    @classmethod
    async def exists_by_filter(
            cls: t.Type[T],
            session: AsyncSession,
            **kwargs,
    ) -> bool:
        """Check if a record exists in the database by a filters."""
        statement = select(cls).filter_by(**kwargs).limit(1)
        result = await session.execute(statement)
        return result.scalars().first() is not None

    @classmethod
    async def paginate(
            cls: t.Type[T],
            session: AsyncSession,
            page_number: int,
            join_tables: t.Union[t.Any, t.List[t.Any]] = None,
            filters: t.Sequence[t.Any] = None,
            order_by: t.Union[Column, None] = None,
    ) -> t.Sequence[T]:
        """Get paginated records from the database by a filters."""
        statement = cls._get_select_statement(join_tables=join_tables, filters=filters, order_by=order_by or cls.id)
        statement = (statement.limit(cls._PAGE_SIZE)
                     .offset((page_number - 1) * cls._PAGE_SIZE))
        result = await session.execute(statement)
        return result.scalars().all()

    @classmethod
    async def paginate_fast(
            cls,
            session: AsyncSession,
            page: int,
            anchor: Anchor | None = None,
            join_tables: t.Union[t.Any, t.List[t.Any]] = None,
            filters: t.Sequence[t.Any] = None,
            direction: int = 1,
            is_deletion: bool = False
    ) -> tuple[t.Sequence[T], Anchor, Anchor]:

        statement = cls._get_select_statement(join_tables=join_tables, filters=filters)
        if direction == 1:
            statement = statement.where(
                cls.id > anchor.value,
            ).order_by(cls.id).limit(cls._PAGE_SIZE)
        else:
            statement = statement.where(
                cls.id < anchor.value if is_deletion else cls.id <= anchor.value,
            ).order_by(desc(cls.id)).limit(cls._PAGE_SIZE)

        result = (await session.execute(statement)).scalars().all()
        if direction == 0:
            result = list(reversed(result))
        if result:
            backward_anchor = Anchor(page=page-1, value=result[0].id)
            forward_anchor = Anchor(page=page+1, value=result[-1].id)

            return result, backward_anchor, forward_anchor

        return [], Anchor(page=page, value=0), Anchor(page=page, value=0)


    @classmethod
    async def total_pages(
            cls: t.Type[T],
            session: AsyncSession,
            join_tables: t.Union[t.Any, t.List[t.Any]] = None,
            filters: t.Sequence[t.Any] = None,
    ) -> int:
        count_col = func.count(cls.id).label("total")
        statement = cls._get_select_statement(count_col, join_tables=join_tables, filters=filters)
        query = await session.execute(statement)
        total = query.scalar() or 0
        return (total + cls._PAGE_SIZE - 1) // cls._PAGE_SIZE


    @classmethod
    async def all(
            cls: t.Type[T],
            session: AsyncSession,
            join_tables: t.Union[t.Any, t.List[t.Any]] = None,
            order_by: t.Union[Column, None] = None,
    ) -> t.Sequence[T]:
        """Get all records from the database."""
        statement = cls._get_select_statement(join_tables=join_tables, order_by=order_by)
        result = await session.execute(statement)
        return result.scalars().all()

    @classmethod
    async def all_by_filter(
            cls: t.Type[T],
            session: AsyncSession,
            join_tables: t.Union[t.Any, t.List[t.Any]] = None,
            order_by: t.Union[Column, None] = None,
            **kwargs,
    ) -> t.Sequence[T]:
        statement = cls._get_select_statement(join_tables=join_tables, filter_by=kwargs, order_by=order_by)
        result = await session.execute(statement)
        return result.scalars().all()
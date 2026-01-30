from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, selectinload, DeclarativeBase
from sqlalchemy import Column, select, func
import typing as t


T = t.TypeVar("T", bound="BaseModel")


class Base(DeclarativeBase):
    pass



class BaseModel(Base):
    __abstract__ = True

    def to_dict(self) -> t.Dict:
        """
        Convert the data to a dictionary.
        """
        return {f"{self.__tablename__}_{col.name}": getattr(self, col.name) for col in
                t.cast(t.List[Column], self.__table__.columns)}

    @staticmethod
    def _get_column(
            model: t.Type[T],
            col: InstrumentedAttribute[t.Any],
    ) -> str:
        """Get the name of a column in a model."""
        name = col.name
        if name not in model.__table__.columns:
            raise ValueError(f"Column {name} not found in {model.__name__}")
        return name

    @classmethod
    def _get_primary_key(cls) -> str:
        """Return the primary key of the model."""
        return cls.__table__.primary_key.columns[0].name

    @classmethod
    async def create(
            cls: t.Type[T],
            session: AsyncSession,
            **kwargs,
    ) -> T:
        """Create a new record in the database."""
        
        instance = cls(**kwargs)
        session.add(instance)
        # await session.refresh(instance)
        return instance

    @classmethod
    async def get(
            cls: t.Type[T],
            session: AsyncSession,
            primary_key: int,
    ) -> T:
        """Get a record from the database by its primary key."""
        
        return await session.get(cls, primary_key)

    @classmethod
    async def get_with_join(
            cls: t.Type[T],
            session: AsyncSession,
            primary_key: int,
            join_tables: t.Union[t.Any, t.List[t.Any]] = None,
    ) -> T:
        """Get a record from the database by its primary key."""
        
        statement = select(cls).filter_by(**{cls._get_primary_key(): primary_key})
        if join_tables is not None:
            statement = statement.options(selectinload(*join_tables))
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
        
        statement = select(cls).filter_by(**{cls._get_column(cls, key): value})
        result = await session.execute(statement)
        return result.scalars().first()

    @classmethod
    async def get_by_filter(
            cls: t.Type[T],
            session: AsyncSession,
            **kwargs,
    ) -> T | None:
        """Get a record from the database by a filters."""
        statement = select(cls).filter_by(**kwargs)
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
        instance = await session.get(cls, primary_key)
        if instance:
            for key, value in kwargs.items():
                setattr(instance, key, value)
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
        
        statement = select(cls).filter_by(**kwargs).order_by(cls.id.asc())  # noqa
        result = await session.execute(statement)
        return bool(result.scalar())

    @classmethod
    async def paginate(
            cls: t.Type[T],
            session: AsyncSession,
            page_number: int,
            page_size: int = 7,
            join_tables: t.Union[t.Any, t.List[t.Any]] = None,
            filters: t.Sequence[t.Any] = None,
            order_by: t.Union[Column, None] = None,
    ) -> t.Sequence[T]:
        """Get paginated records from the database by a filters."""
        
        statement = (
            select(cls)
            .limit(page_size).offset((page_number - 1) * page_size)
        )
        if filters is not None:
            statement = statement.filter(*filters)
        if join_tables is not None:
            statement = statement.join(*join_tables).options(selectinload(*join_tables))
        if order_by is not None:
            statement = statement.order_by(order_by)
        result = await session.execute(statement)
        return result.scalars().all()

    @classmethod
    async def total_pages(
            cls: t.Type[T],
            session: AsyncSession,
            page_size: int = 7,
            join_tables: t.Union[t.Any, t.List[t.Any]] = None,
            filters: t.Sequence[t.Any] = None,
    ) -> int:
        
        statement = select(func.count(cls.__table__.primary_key.columns[0]))
        if filters is not None:
            statement = statement.filter(*filters)
        if join_tables is not None:
            statement = statement.join(*join_tables)
        query = await session.execute(statement)
        return (query.scalar() + page_size - 1) // page_size


    @classmethod
    async def all(
            cls: t.Type[T],
            session: AsyncSession,
            join_tables: t.Union[t.Any, t.List[t.Any]] = None,
            order_by: t.Union[Column, None] = None,
    ) -> t.Sequence[T]:
        """Get all records from the database."""
        
        statement = select(cls)
        if join_tables is not None:
            statement = statement.options(selectinload(*join_tables))
        if order_by:
            statement = statement.order_by(order_by)
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
        """Get all records from the database by a filters."""
        
        statement = select(cls).filter_by(**kwargs)
        if join_tables is not None:
            statement = statement.options(selectinload(*join_tables))
        if order_by:
            statement = statement.order_by(order_by)
        result = await session.execute(statement)
        return result.scalars().all()
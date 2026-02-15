from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, selectinload, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Column, select, func, Integer, BigInteger
import typing as t


T = t.TypeVar("T", bound="BaseModel")


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True
    _must_be_active = False

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    def to_dict(self) -> t.Dict:
        """
        Convert the data to a dictionary.
        """
        return {f"{self.__tablename__}_{col.name}": getattr(self, col.name) for col in
                t.cast(t.List[Column], t.cast(object, self.__table__.columns))}

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
        if select_value:
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
        statement = cls._get_select_statement(filter_by=filter_by,
                                              join_tables=join_tables)
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
            page_size: int = 7,
            join_tables: t.Union[t.Any, t.List[t.Any]] = None,
            filters: t.Sequence[t.Any] = None,
            order_by: t.Union[Column, None] = None,
    ) -> t.Sequence[T]:
        """Get paginated records from the database by a filters."""
        statement = cls._get_select_statement(
            join_tables=join_tables,
            filters=filters,
            order_by=order_by,
        )
        statement = statement.limit(page_size).offset((page_number - 1) * page_size)
        result = await session.execute(statement)
        return result.scalars().all()

    @classmethod
    async def paginate_fast(
            cls,
            session: AsyncSession,
            page_size: int = 7,
            anchor: int | None = None,
            join_tables: t.Union[t.Any, t.List[t.Any]] = None,
            filters: t.Sequence[t.Any] = None,
            order_by: t.Union[Column, None] = None,
    ) -> tuple[t.Sequence[T], int]:
        if not anchor:
            result = await cls.paginate(
                session,
                1,
                page_size,
                join_tables,
                filters,
                order_by
            )
        else:
            statement = cls._get_select_statement(
                join_tables=join_tables,
                filters=filters,
                order_by=order_by,
            )
            statement = statement.where(
                cls.id > anchor,
            ).order_by(cls.id).limit(page_size)

            result = (await session.execute(statement)).scalars().all()
        if result:
            return result, result[-1].id
        return result, 0


    @classmethod
    async def total_pages(
            cls: t.Type[T],
            session: AsyncSession,
            page_size: int = 7,
            join_tables: t.Union[t.Any, t.List[t.Any]] = None,
            filters: t.Sequence[t.Any] = None,
    ) -> int:
        count_col = func.count().label("total")
        statement = cls._get_select_statement(
            count_col,
            join_tables=join_tables,
            filters=filters,
        )
        query = await session.execute(statement)
        total = query.scalar() or 0
        return (total + page_size - 1) // page_size


    @classmethod
    async def all(
            cls: t.Type[T],
            session: AsyncSession,
            join_tables: t.Union[t.Any, t.List[t.Any]] = None,
            order_by: t.Union[Column, None] = None,
    ) -> t.Sequence[T]:
        """Get all records from the database."""
        statement = cls._get_select_statement(
            join_tables=join_tables,
            order_by=order_by,
        )
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
        statement = cls._get_select_statement(
            join_tables=join_tables,
            filter_by=kwargs,
            order_by=order_by,
        )
        result = await session.execute(statement)
        return result.scalars().all()
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from project.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args=settings.DATABASE_CONNECT_DICT,
    echo="debug", pool_pre_ping=True, poolclass=NullPool
)
Base = declarative_base()


async def get_session() -> AsyncSession:
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False
    )
    async with async_session() as session:
        yield session


async def connect() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)


async def disconnect() -> None:
    if engine:
        await engine.dispose()

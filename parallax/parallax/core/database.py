"""
Database engine and session management for PARALLAX.

Uses SQLAlchemy async engine with asyncpg for PostgreSQL.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from parallax.core.config import settings

DATABASE_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_SERVER}/{settings.POSTGRES_DB}"
)

engine = create_async_engine(DATABASE_URL, echo=(settings.ENVIRONMENT == "development"))

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


async def get_session() -> AsyncSession:
    """Dependency that yields an async DB session."""
    async with async_session() as session:
        yield session

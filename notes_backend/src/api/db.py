import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Set it in the container environment (.env)."
        )
    return value


def _build_async_database_url() -> str:
    """
    Build an async SQLAlchemy URL for PostgreSQL using the container-provided env vars.

    Note: We intentionally do not assume POSTGRES_URL is already a fully qualified DSN.
    We derive a DSN from the standard POSTGRES_* variables used by this project.
    """
    host = _require_env("POSTGRES_URL")
    user = _require_env("POSTGRES_USER")
    password = _require_env("POSTGRES_PASSWORD")
    db = _require_env("POSTGRES_DB")
    port = _require_env("POSTGRES_PORT")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


_engine = create_async_engine(
    _build_async_database_url(),
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(bind=_engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session."""
    async with AsyncSessionLocal() as session:
        yield session

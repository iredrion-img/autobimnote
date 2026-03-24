"""
app/core/database.py – Async SQLAlchemy engine.

Automatically selects the right dialect via settings.resolved_database_url:
  - SQLite  → aiosqlite  (local dev, no server needed)
  - PostgreSQL → asyncpg  (Cloud SQL / production)
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# ── Engine ─────────────────────────────────────────────────────────────────────
_db_url = settings.resolved_database_url
_connect_args: dict = {}

if "sqlite" in _db_url:
    _connect_args = {"check_same_thread": False}

engine = create_async_engine(
    _db_url,
    echo=settings.DEBUG,
    connect_args=_connect_args,
    pool_pre_ping=True,
)

# ── Session factory ────────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# ── Declarative base ───────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Dependency ─────────────────────────────────────────────────────────────────
async def get_db() -> AsyncSession:
    """FastAPI dependency that yields a DB session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

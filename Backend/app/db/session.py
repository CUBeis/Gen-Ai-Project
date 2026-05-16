"""
app/db/session.py
──────────────────
Async SQLAlchemy engine, session factory, and declarative Base.

Everything database-related imports from here:
    from app.db.session import AsyncSessionLocal, Base, engine

The engine is created once at module load time.
Sessions are created per-request via the get_db() dependency in core/dependencies.py.

Connection pool settings are tuned for a production FastAPI application:
  - pool_size=10       : up to 10 persistent connections (one per Uvicorn worker)
  - max_overflow=20    : allow 20 extra connections under burst load
  - pool_pre_ping=True : test connection liveness before using (handles DB restarts)
  - pool_recycle=1800  : recycle connections every 30 min (avoids stale connection errors)
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# ── Declarative Base ───────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """
    Base class for all ORM models.
    Import this in every model file and inherit from it.
    Alembic's env.py imports this to auto-detect schema changes.
    """
    pass


# ── Async Engine ───────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,          # log SQL in development; silent in production
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,           # validate connection before checkout
    pool_recycle=1800,            # recycle stale connections every 30 minutes
    # asyncpg driver specifics
    connect_args={
        "server_settings": {
            "application_name": "nerve_ai_api",
            "timezone": "UTC",
        }
    },
)


# ── Session Factory ────────────────────────────────────────────────────────────
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,    # keep attributes accessible after commit
    autocommit=False,
    autoflush=False,
)
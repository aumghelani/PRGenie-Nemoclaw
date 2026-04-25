"""
SQLite engine + session factory.

The engine URL comes from settings.DATABASE_URL. For tests, call
init_engine("sqlite://") to get an in-memory engine instead.
"""
from __future__ import annotations

from sqlmodel import Session, SQLModel, create_engine

from backend.config import settings

# A single module-level engine. Tests override via init_engine("sqlite://").
_engine = None


def _make_engine(url: str):
    # check_same_thread=False is required for SQLite + FastAPI threading.
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


def init_engine(url: str | None = None):
    """Create (or reset) the global engine and create all tables."""
    global _engine
    _engine = _make_engine(url or settings.DATABASE_URL)
    # Import models so SQLModel metadata sees them.
    from backend.db import models  # noqa: F401
    SQLModel.metadata.create_all(_engine)
    return _engine


def get_engine():
    if _engine is None:
        init_engine()
    return _engine


def get_session() -> Session:
    """Synchronous session — SQLite is fine without async, and SQLModel
    doesn't have first-class async support."""
    return Session(get_engine())

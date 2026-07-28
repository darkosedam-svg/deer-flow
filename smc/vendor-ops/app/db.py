"""Database setup. SQLite by default (fine for tests and a single-VPS deploy
start); point DATABASE_URL at Postgres in production. Alembic migrations get
added when the schema stabilizes (pre-M6 gate).

The engine is created lazily from the environment on first use so tests can
point each case at a fresh temp database via reset_engine()."""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

_engine = None
_SessionLocal = None


class Base(DeclarativeBase):
    pass


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        url = os.environ.get("DATABASE_URL", "sqlite:///vendor_ops.db")
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args)
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def reset_engine() -> None:
    """Drop the cached engine so the next use re-reads DATABASE_URL (tests)."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_session() -> Session:
    get_engine()
    return _SessionLocal()


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(get_engine())

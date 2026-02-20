# app/db.py
from __future__ import annotations

from contextlib import contextmanager
from typing import Optional, cast

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.settings import get_settings

_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def _init_engine() -> None:
    """Initialize engine + sessionmaker once (lazy).

    We keep DB init lazy so process bootstrap can configure tracing/logging first,
    then create/instrument the engine deterministically.
    """
    global _engine, _SessionLocal
    if _engine is not None and _SessionLocal is not None:
        return

    settings = get_settings()
    _engine = create_engine(settings.DATABASE_URL, future=True)

    _SessionLocal = sessionmaker(
        bind=_engine,
        autoflush=False,
        autocommit=False,
        future=True,
        expire_on_commit=False,  # <-- evita DetachedInstanceError su response models
    )


def get_engine() -> Engine:
    _init_engine()
    return cast(Engine, _engine)


def get_sessionmaker() -> sessionmaker:
    _init_engine()
    return cast(sessionmaker, _SessionLocal)


class _EngineProxy:
    """Back-compat proxy for `from app.db import engine`.

    Prefer using `get_engine()` in new code.
    """

    def __getattr__(self, name: str):
        return getattr(get_engine(), name)

    def __repr__(self) -> str:  # pragma: no cover
        return repr(get_engine())


# Backward compatible symbol; do not eagerly create the real engine.
engine = _EngineProxy()

class _SessionLocalProxy:
    """Back-compat proxy for `from app.db import SessionLocal`.

    Tests (and possibly some code) expect `SessionLocal()` to return a Session.
    With lazy init, we provide a callable proxy that creates the session on demand.
    """

    def __call__(self):
        return get_sessionmaker()()

    def __getattr__(self, name: str):
        return getattr(get_sessionmaker(), name)

# Backward compatible symbol; do not eagerly create the real sessionmaker.
SessionLocal = _SessionLocalProxy()


@contextmanager
def get_session():
    SessionLocal = get_sessionmaker()
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

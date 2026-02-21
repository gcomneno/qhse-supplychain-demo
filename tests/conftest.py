# tests/conftest.py
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app import db as app_db
from app.main import app  # se il tuo entrypoint è diverso, cambia qui

from dotenv import load_dotenv


# Carica .env SOLO se presente (locale). In CI di norma non c'è.
load_dotenv(override=False)


def _require_test_db_url() -> str:
    # Demo mode: se TEST_DATABASE_URL non c'è, usiamo DATABASE_URL.
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "Serve TEST_DATABASE_URL o DATABASE_URL. "
            "Esempio: postgresql+psycopg://qhse:qhse@127.0.0.1:5432/qhse"
        )
    if url.startswith("sqlite:"):
        raise RuntimeError("DB per test non può essere SQLite. Postgres-only.")
    return url


@pytest.fixture(scope="session", autouse=True)
def force_test_database_url():
    """
    Durante i test, DATABASE_URL deve essere coerente col DB effettivo usato.
    Evita interferenze da env 'sporche'.
    """
    test_url = _require_test_db_url()

    prev_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_url

    # opzionale: evita rumore/instabilità nei test
    os.environ.setdefault("ENABLE_TRACING", "0")
    os.environ.setdefault("TRACE_SAMPLING", "0")

    yield

    if prev_db_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = prev_db_url


@pytest.fixture(scope="session")
def engine():
    return app_db.get_engine()


@pytest.fixture(scope="session", autouse=True)
def bind_app_db_to_test_engine(engine):
    """
    Forza app_db.SessionLocal a puntare al Postgres dei test.

    NOTA: non usiamo la fixture monkeypatch (function-scoped), ma MonkeyPatch manuale.
    """
    mp = pytest.MonkeyPatch()

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )

    # Se nel modulo db esiste un attr 'engine' (compat), lo allineiamo.
    if hasattr(app_db, "engine"):
        mp.setattr(app_db, "engine", engine, raising=False)

    mp.setattr(app_db, "SessionLocal", TestingSessionLocal, raising=True)

    yield

    mp.undo()


@pytest.fixture(autouse=True)
def db_clean_between_tests(engine):
    """
    Reset deterministico tra test:
    TRUNCATE di tutte le tabelle in schema public (eccetto alembic_version),
    RESTART IDENTITY, CASCADE.
    """
    with engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        conn.execute(
            text(
                """
DO $$
DECLARE
    stmt text;
BEGIN
    SELECT
        'TRUNCATE TABLE ' ||
        string_agg(format('%I.%I', schemaname, tablename), ', ') ||
        ' RESTART IDENTITY CASCADE'
    INTO stmt
    FROM pg_tables
    WHERE schemaname = 'public'
      AND tablename <> 'alembic_version';

    IF stmt IS NOT NULL THEN
        EXECUTE stmt;
    END IF;
END $$;
"""
            )
        )
    yield


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session", autouse=True)
def shutdown_otel_at_end():
    """
    Evita il rumore:
    'ValueError: I/O operation on closed file'
    causato da exporter/thread OTel ancora vivo a fine pytest.
    """
    yield
    try:
        from opentelemetry import trace

        tp = trace.get_tracer_provider()
        shutdown = getattr(tp, "shutdown", None)
        if callable(shutdown):
            shutdown()
    except Exception:
        # mai far fallire i test per cleanup observability
        pass

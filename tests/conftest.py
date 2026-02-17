# tests/conftest.py
from __future__ import annotations

import os
os.environ["DATABASE_URL"] = "sqlite:///./qhse_demo.sqlite3"
os.environ["ENV"] = "test"

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import db as app_db
from app.models import Base
from app.main import app  # se il tuo entrypoint ha un altro nome, cambia qui


@pytest.fixture()
def test_engine(tmp_path: Path):
    db_path = tmp_path / "test.sqlite3"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, test_engine):
    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )

    monkeypatch.setattr(app_db, "engine", test_engine, raising=True)
    monkeypatch.setattr(app_db, "SessionLocal", TestingSessionLocal, raising=True)

    with TestClient(app) as c:
        yield c

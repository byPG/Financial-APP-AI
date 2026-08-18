"""Fixtures for the Backend Engineer's test suite (backend/tests/app/).

Every test gets its own isolated SQLite file (via the DB_PATH env var
override — see app/db/connection.py) and LLM_MOCK=true, so nothing here
ever touches a shared database or makes a real network call.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.db.connection import get_connection
from app.db.schema import init_db
from app.market_data.simulator import MarketSimulator


@pytest.fixture
def db_path(tmp_path, monkeypatch) -> str:
    path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", path)
    monkeypatch.setenv("LLM_MOCK", "true")
    return path


@pytest.fixture
def client(db_path) -> Iterator[TestClient]:
    """A TestClient wired to a fresh, isolated database via the lifespan
    handler (app.main.lifespan reads DB_PATH at startup, seeds the default
    watchlist, and starts a real MarketSimulator since MASSIVE_API_KEY is
    unset in the test environment)."""
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_conn(db_path) -> Iterator[sqlite3.Connection]:
    """A direct, already-initialized (schema created + seeded) connection to
    the same isolated DB, for tests that exercise business-logic functions
    directly or assert on rows rather than going through the API."""
    conn = get_connection()
    init_db(conn)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def provider() -> MarketSimulator:
    """A standalone simulator instance for unit tests that exercise
    portfolio/watchlist business-logic functions directly (not through the
    API), without needing the async background tick loop running."""
    sim = MarketSimulator(seed=1234)
    return sim

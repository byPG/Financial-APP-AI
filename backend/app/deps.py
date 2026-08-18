"""FastAPI dependency providers shared across routers."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator

from fastapi import Request

from app.db.connection import get_connection
from app.market_data.base import MarketDataProvider


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """One short-lived connection per request, closed when the request ends
    (planning/PLAN.md Section 7, Concurrency & Safety)."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def get_provider(request: Request) -> MarketDataProvider:
    """The single market data provider instance, created at startup in
    app.main's lifespan handler and stashed on app.state."""
    return request.app.state.provider

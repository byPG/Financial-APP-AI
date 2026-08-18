"""Database layer: connection management + schema/seed logic. See
docs/ARCHITECTURE.md Section 2 and planning/PLAN.md Section 7.
"""

from __future__ import annotations

from app.db.connection import get_connection, get_db_path
from app.db.schema import (
    DEFAULT_CASH_BALANCE,
    DEFAULT_USER_ID,
    DEFAULT_WATCHLIST_TICKERS,
    init_db,
)

__all__ = [
    "DEFAULT_CASH_BALANCE",
    "DEFAULT_USER_ID",
    "DEFAULT_WATCHLIST_TICKERS",
    "get_connection",
    "get_db_path",
    "init_db",
]

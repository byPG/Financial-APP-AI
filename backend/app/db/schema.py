"""SQLite schema (DDL) and lazy seed logic. See planning/PLAN.md Section 7.

All tables carry a ``user_id`` column defaulting to ``"default"`` — hardcoded
single-user for now, but keeps the schema forward-compatible with multi-user
support without a migration.

``positions`` and ``watchlist`` each add a ``UNIQUE(user_id, ticker)``
constraint. ``watchlist``'s is specified directly in planning/PLAN.md
Section 7. ``positions``' is not spelled out there, but the product rules in
Section 14 (one avg-cost position per ticker, deleted at zero quantity) only
make sense with at most one position row per ticker — this is an additive,
non-contract-breaking implementation detail, not a change to any documented
shape.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

DEFAULT_USER_ID = "default"
DEFAULT_CASH_BALANCE = 10000.0

# planning/PLAN.md Section 15 — default ticker universe.
DEFAULT_WATCHLIST_TICKERS: tuple[str, ...] = (
    "AAPL",
    "GOOGL",
    "MSFT",
    "AMZN",
    "TSLA",
    "NVDA",
    "META",
    "JPM",
    "V",
    "NFLX",
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users_profile (
    id TEXT PRIMARY KEY,
    cash_balance REAL NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlist (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    added_at TEXT NOT NULL,
    UNIQUE (user_id, ticker)
);

CREATE TABLE IF NOT EXISTS positions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    quantity REAL NOT NULL,
    avg_cost REAL NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (user_id, ticker)
);

CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    executed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    total_value REAL NOT NULL,
    recorded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    actions TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_trades_user ON trades (user_id, executed_at);
CREATE INDEX IF NOT EXISTS idx_snapshots_user ON portfolio_snapshots (user_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages (user_id, created_at);
"""


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def init_db(conn: sqlite3.Connection) -> None:
    """Lazily initialize the database: create tables if missing, then seed
    default data if the ``"default"`` user profile doesn't exist yet.

    Safe to call on every process startup — ``CREATE TABLE IF NOT EXISTS``
    is a no-op against an existing schema, and seeding is skipped entirely
    once the default profile row exists, so re-init never duplicates data.
    """
    conn.executescript(SCHEMA_SQL)

    row = conn.execute(
        "SELECT id FROM users_profile WHERE id = ?", (DEFAULT_USER_ID,)
    ).fetchone()
    if row is not None:
        return

    now = _now_iso()
    conn.execute(
        "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
        (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, now),
    )
    for ticker in DEFAULT_WATCHLIST_TICKERS:
        conn.execute(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (str(uuid4()), DEFAULT_USER_ID, ticker, now),
        )
    conn.commit()

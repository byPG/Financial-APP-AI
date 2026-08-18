"""DB init/seeding tests. See backend/app/db/schema.py."""

from __future__ import annotations

from app.db.connection import get_connection
from app.db.schema import (
    DEFAULT_CASH_BALANCE,
    DEFAULT_USER_ID,
    DEFAULT_WATCHLIST_TICKERS,
    init_db,
)


def test_fresh_db_gets_seeded(db_path):
    conn = get_connection()
    try:
        init_db(conn)

        profile = conn.execute(
            "SELECT id, cash_balance FROM users_profile WHERE id = ?", (DEFAULT_USER_ID,)
        ).fetchone()
        assert profile is not None
        assert profile["cash_balance"] == DEFAULT_CASH_BALANCE

        tickers = {
            row["ticker"]
            for row in conn.execute(
                "SELECT ticker FROM watchlist WHERE user_id = ?", (DEFAULT_USER_ID,)
            ).fetchall()
        }
        assert tickers == set(DEFAULT_WATCHLIST_TICKERS)
    finally:
        conn.close()


def test_reinit_on_existing_db_does_not_duplicate(db_path):
    conn = get_connection()
    try:
        init_db(conn)
        init_db(conn)  # second call: schema already exists, profile already seeded

        profile_count = conn.execute(
            "SELECT COUNT(*) AS n FROM users_profile WHERE id = ?", (DEFAULT_USER_ID,)
        ).fetchone()["n"]
        assert profile_count == 1

        watchlist_count = conn.execute(
            "SELECT COUNT(*) AS n FROM watchlist WHERE user_id = ?", (DEFAULT_USER_ID,)
        ).fetchone()["n"]
        assert watchlist_count == len(DEFAULT_WATCHLIST_TICKERS)
    finally:
        conn.close()


def test_reinit_across_separate_connections_does_not_duplicate(db_path):
    """Simulates two process startups against the same file (e.g. container
    restart): a brand new connection re-running init_db should be a no-op,
    not a re-seed."""
    conn1 = get_connection()
    try:
        init_db(conn1)
    finally:
        conn1.close()

    conn2 = get_connection()
    try:
        init_db(conn2)
        watchlist_count = conn2.execute(
            "SELECT COUNT(*) AS n FROM watchlist WHERE user_id = ?", (DEFAULT_USER_ID,)
        ).fetchone()["n"]
        assert watchlist_count == len(DEFAULT_WATCHLIST_TICKERS)
    finally:
        conn2.close()

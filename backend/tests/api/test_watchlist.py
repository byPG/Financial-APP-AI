"""Watchlist business logic + API tests. See planning/PLAN.md Section 14
(Ticker Scope) and docs/ARCHITECTURE.md Section 4.
"""

from __future__ import annotations

import pytest

from app.errors import ConflictError, NotFoundError, ValidationError
from app.portfolio import execute_trade
from app.watchlist import add_ticker, list_watchlist, remove_ticker


def test_add_new_ticker(db_conn, provider):
    item = add_ticker(db_conn, provider, "IBM")
    assert item.ticker == "IBM"
    assert item.current_price is not None  # provider.watch() was called

    row = db_conn.execute("SELECT ticker FROM watchlist WHERE ticker = 'IBM'").fetchone()
    assert row is not None


def test_add_ticker_is_idempotent(db_conn, provider):
    first = add_ticker(db_conn, provider, "IBM")
    second = add_ticker(db_conn, provider, "IBM")

    assert first.added_at == second.added_at
    count = db_conn.execute(
        "SELECT COUNT(*) AS n FROM watchlist WHERE ticker = 'IBM'"
    ).fetchone()["n"]
    assert count == 1


def test_add_ticker_lowercase_is_normalized(db_conn, provider):
    item = add_ticker(db_conn, provider, "ibm")
    assert item.ticker == "IBM"


def test_add_ticker_invalid_format_raises(db_conn, provider):
    with pytest.raises(ValidationError):
        add_ticker(db_conn, provider, "TOOLONG")
    with pytest.raises(ValidationError):
        add_ticker(db_conn, provider, "12345")


def test_remove_ticker_not_found_raises(db_conn, provider):
    with pytest.raises(NotFoundError):
        remove_ticker(db_conn, provider, "ZZZZZ")


def test_remove_ticker_success(db_conn, provider):
    add_ticker(db_conn, provider, "IBM")
    remove_ticker(db_conn, provider, "IBM")

    row = db_conn.execute("SELECT ticker FROM watchlist WHERE ticker = 'IBM'").fetchone()
    assert row is None
    assert provider.get_latest("IBM") is None  # unwatch() was called


def test_remove_ticker_with_open_position_raises_conflict(db_conn, provider):
    add_ticker(db_conn, provider, "IBM")
    execute_trade(db_conn, provider, "IBM", 1, "buy")

    with pytest.raises(ConflictError):
        remove_ticker(db_conn, provider, "IBM")

    # still present
    row = db_conn.execute("SELECT ticker FROM watchlist WHERE ticker = 'IBM'").fetchone()
    assert row is not None


def test_remove_ticker_after_position_closed_succeeds(db_conn, provider):
    add_ticker(db_conn, provider, "IBM")
    execute_trade(db_conn, provider, "IBM", 1, "buy")
    execute_trade(db_conn, provider, "IBM", 1, "sell")

    remove_ticker(db_conn, provider, "IBM")  # should not raise

    row = db_conn.execute("SELECT ticker FROM watchlist WHERE ticker = 'IBM'").fetchone()
    assert row is None


def test_list_watchlist_includes_prices(db_conn, provider):
    add_ticker(db_conn, provider, "IBM")
    result = list_watchlist(db_conn, provider)
    ibm_items = [item for item in result.items if item.ticker == "IBM"]
    assert len(ibm_items) == 1
    assert ibm_items[0].current_price is not None


# --- API-level tests ---


def test_api_default_watchlist_has_ten_tickers(client):
    resp = client.get("/api/watchlist")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 10


def test_api_add_ticker_200_and_idempotent(client):
    resp = client.post("/api/watchlist", json={"ticker": "IBM"})
    assert resp.status_code == 200
    assert resp.json()["ticker"] == "IBM"

    resp2 = client.post("/api/watchlist", json={"ticker": "IBM"})
    assert resp2.status_code == 200


def test_api_add_ticker_bad_format_400(client):
    resp = client.post("/api/watchlist", json={"ticker": "toolongticker"})
    assert resp.status_code == 400


def test_api_remove_ticker_404(client):
    resp = client.delete("/api/watchlist/ZZZZZ")
    assert resp.status_code == 404


def test_api_remove_ticker_409_with_open_position(client):
    client.post("/api/watchlist", json={"ticker": "IBM"})
    client.post("/api/portfolio/trade", json={"ticker": "IBM", "quantity": 1, "side": "buy"})

    resp = client.delete("/api/watchlist/IBM")
    assert resp.status_code == 409


def test_api_remove_ticker_204(client):
    client.post("/api/watchlist", json={"ticker": "IBM"})
    resp = client.delete("/api/watchlist/IBM")
    assert resp.status_code == 204

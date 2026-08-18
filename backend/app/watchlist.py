"""Watchlist business logic + the /api/watchlist routes. See
planning/PLAN.md Section 14 (Ticker Scope) and docs/ARCHITECTURE.md Section 4.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, Response

from app.db.schema import DEFAULT_USER_ID
from app.deps import get_db, get_provider
from app.errors import ConflictError, NotFoundError, ValidationError
from app.market_data.base import MarketDataProvider
from app.schemas import AddTickerRequest, WatchlistItemResponse, WatchlistResponse
from app.tickers import is_valid_ticker

router = APIRouter(prefix="/api", tags=["watchlist"])


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _item_response(
    provider: MarketDataProvider, ticker: str, added_at: str
) -> WatchlistItemResponse:
    snapshot = provider.get_latest(ticker)
    return WatchlistItemResponse(
        ticker=ticker,
        added_at=added_at,
        current_price=snapshot.price if snapshot is not None else None,
        previous_price=snapshot.previous_price if snapshot is not None else None,
    )


def list_watchlist(
    conn: sqlite3.Connection,
    provider: MarketDataProvider,
    user_id: str = DEFAULT_USER_ID,
) -> WatchlistResponse:
    rows = conn.execute(
        "SELECT ticker, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at ASC",
        (user_id,),
    ).fetchall()
    return WatchlistResponse(
        items=[_item_response(provider, row["ticker"], row["added_at"]) for row in rows]
    )


def add_ticker(
    conn: sqlite3.Connection,
    provider: MarketDataProvider,
    ticker: str,
    user_id: str = DEFAULT_USER_ID,
) -> WatchlistItemResponse:
    ticker = ticker.upper()
    if not is_valid_ticker(ticker):
        raise ValidationError(f"invalid ticker format: {ticker!r}")

    existing = conn.execute(
        "SELECT added_at FROM watchlist WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    ).fetchone()
    if existing is not None:
        # docs/ARCHITECTURE.md Section 4: idempotent — 200 with the existing
        # entry, not an error.
        return _item_response(provider, ticker, existing["added_at"])

    now = _now_iso()
    conn.execute(
        "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
        (str(uuid4()), user_id, ticker, now),
    )
    conn.commit()
    provider.watch(ticker)
    return _item_response(provider, ticker, now)


def remove_ticker(
    conn: sqlite3.Connection,
    provider: MarketDataProvider,
    ticker: str,
    user_id: str = DEFAULT_USER_ID,
) -> None:
    ticker = ticker.upper()
    existing = conn.execute(
        "SELECT ticker FROM watchlist WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    ).fetchone()
    if existing is None:
        raise NotFoundError(f"{ticker} is not on the watchlist")

    position_row = conn.execute(
        "SELECT quantity FROM positions WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    ).fetchone()
    if position_row is not None and position_row["quantity"] > 0:
        raise ConflictError(f"cannot remove {ticker}: an open position exists")

    conn.execute("DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker))
    conn.commit()
    provider.unwatch(ticker)


# --- Routes ---


@router.get("/watchlist", response_model=WatchlistResponse)
def get_watchlist_route(
    conn: sqlite3.Connection = Depends(get_db),
    provider: MarketDataProvider = Depends(get_provider),
) -> WatchlistResponse:
    return list_watchlist(conn, provider)


@router.post("/watchlist", response_model=WatchlistItemResponse)
def post_watchlist_route(
    add_request: AddTickerRequest,
    conn: sqlite3.Connection = Depends(get_db),
    provider: MarketDataProvider = Depends(get_provider),
) -> WatchlistItemResponse:
    return add_ticker(conn, provider, add_request.ticker)


@router.delete("/watchlist/{ticker}", status_code=204)
def delete_watchlist_route(
    ticker: str,
    conn: sqlite3.Connection = Depends(get_db),
    provider: MarketDataProvider = Depends(get_provider),
) -> Response:
    remove_ticker(conn, provider, ticker)
    return Response(status_code=204)

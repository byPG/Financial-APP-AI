"""Portfolio business logic (trade execution, P&L, snapshots) + the
/api/portfolio routes. See planning/PLAN.md Section 14 and
docs/ARCHITECTURE.md Section 4.

Business-logic functions take an explicit ``sqlite3.Connection`` and
``MarketDataProvider`` rather than reading FastAPI dependencies directly, so
chat.py can call ``execute_trade`` for LLM-issued trades through the exact
same validated path as the manual REST endpoint (planning/REVIEW.md item
18 — never bypass validation because the source is the LLM).
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.db.schema import DEFAULT_USER_ID
from app.deps import get_db, get_provider
from app.errors import ValidationError
from app.market_data.base import MarketDataProvider
from app.schemas import (
    PortfolioHistoryResponse,
    PortfolioResponse,
    PortfolioSnapshotResponse,
    PositionResponse,
    TradeRecord,
    TradeRequest,
    TradeResponse,
)
from app.tickers import is_valid_ticker

# Floating point trades: guard equality/comparisons with a small epsilon so
# "sell exactly what you own" and "spend exactly your cash balance" don't
# spuriously fail from binary floating point representation error.
_EPSILON = 1e-9

PORTFOLIO_HISTORY_LIMIT = 500

router = APIRouter(prefix="/api", tags=["portfolio"])


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _get_cash_balance(conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID) -> float:
    row = conn.execute(
        "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
    ).fetchone()
    if row is None:
        raise RuntimeError(f"users_profile row missing for user_id={user_id!r}; db not initialized")
    return row["cash_balance"]


def _get_position_rows(
    conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID
) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ? ORDER BY ticker",
        (user_id,),
    ).fetchall()


def get_portfolio(
    conn: sqlite3.Connection,
    provider: MarketDataProvider,
    user_id: str = DEFAULT_USER_ID,
) -> PortfolioResponse:
    cash_balance = _get_cash_balance(conn, user_id)
    rows = _get_position_rows(conn, user_id)

    positions: list[PositionResponse] = []
    total_market_value = 0.0
    total_unrealized_pnl = 0.0

    for row in rows:
        snapshot = provider.get_latest(row["ticker"])
        # A position can in principle outlive its watchlist entry only
        # transiently (removal is blocked by watchlist.py while a position
        # is open) — fall back to avg_cost so P&L math never crashes even
        # if that invariant is ever violated out-of-band.
        current_price = snapshot.price if snapshot is not None else row["avg_cost"]
        quantity = row["quantity"]
        avg_cost = row["avg_cost"]

        market_value = current_price * quantity
        unrealized_pnl = (current_price - avg_cost) * quantity
        cost_basis = avg_cost * quantity
        unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100.0) if cost_basis else 0.0

        positions.append(
            PositionResponse(
                ticker=row["ticker"],
                quantity=quantity,
                avg_cost=avg_cost,
                current_price=current_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct,
            )
        )
        total_market_value += market_value
        total_unrealized_pnl += unrealized_pnl

    return PortfolioResponse(
        cash_balance=cash_balance,
        positions=positions,
        total_value=cash_balance + total_market_value,
        total_unrealized_pnl=total_unrealized_pnl,
    )


def execute_trade(
    conn: sqlite3.Connection,
    provider: MarketDataProvider,
    ticker: str,
    quantity: float,
    side: str,
    user_id: str = DEFAULT_USER_ID,
) -> TradeRecord:
    """Execute a market order at the current cached price. Cash + position
    updates commit atomically in one transaction. Raises ValidationError
    (-> 400) for any rule violation; never partially applies a trade.
    """
    ticker = ticker.upper()
    if not is_valid_ticker(ticker):
        raise ValidationError(f"invalid ticker format: {ticker!r}")
    if quantity <= 0:
        raise ValidationError("quantity must be greater than zero")
    if side not in ("buy", "sell"):
        raise ValidationError(f"invalid side: {side!r}")

    # planning/PLAN.md Section 14, Ticker Scope: a trade is only valid for a
    # ticker currently on the watchlist. get_latest(...) is None for
    # anything not watched, which is the practical enforcement signal
    # (docs/ARCHITECTURE.md Section 3).
    snapshot = provider.get_latest(ticker)
    if snapshot is None:
        raise ValidationError(f"{ticker} is not on the watchlist")
    price = snapshot.price

    cash_balance = _get_cash_balance(conn, user_id)
    position_row = conn.execute(
        "SELECT quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    ).fetchone()

    now = _now_iso()

    if side == "buy":
        cost = quantity * price
        if cost > cash_balance + _EPSILON:
            raise ValidationError(
                f"insufficient cash: need {cost:.2f}, have {cash_balance:.2f}"
            )
        new_cash_balance = cash_balance - cost

        if position_row is None:
            new_quantity = quantity
            new_avg_cost = price
            conn.execute(
                "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid4()), user_id, ticker, new_quantity, new_avg_cost, now),
            )
        else:
            old_quantity = position_row["quantity"]
            old_avg_cost = position_row["avg_cost"]
            new_quantity = old_quantity + quantity
            new_avg_cost = ((old_quantity * old_avg_cost) + (quantity * price)) / new_quantity
            conn.execute(
                "UPDATE positions SET quantity = ?, avg_cost = ?, updated_at = ? "
                "WHERE user_id = ? AND ticker = ?",
                (new_quantity, new_avg_cost, now, user_id, ticker),
            )
    else:  # sell
        owned = position_row["quantity"] if position_row is not None else 0.0
        if owned < quantity - _EPSILON:
            raise ValidationError(f"insufficient shares: own {owned}, tried to sell {quantity}")
        proceeds = quantity * price
        new_cash_balance = cash_balance + proceeds
        remaining = owned - quantity

        if remaining <= _EPSILON:
            # planning/REVIEW.md item 25: position row is deleted at zero
            # quantity; no realized P&L tracking (deferred out of v1 scope).
            conn.execute(
                "DELETE FROM positions WHERE user_id = ? AND ticker = ?", (user_id, ticker)
            )
        else:
            conn.execute(
                "UPDATE positions SET quantity = ?, updated_at = ? WHERE user_id = ? AND ticker = ?",
                (remaining, now, user_id, ticker),
            )

    conn.execute(
        "UPDATE users_profile SET cash_balance = ? WHERE id = ?", (new_cash_balance, user_id)
    )
    trade_id = str(uuid4())
    conn.execute(
        "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (trade_id, user_id, ticker, side, quantity, price, now),
    )
    conn.commit()

    return TradeRecord(
        id=trade_id, ticker=ticker, side=side, quantity=quantity, price=price, executed_at=now
    )


def record_snapshot(
    conn: sqlite3.Connection, provider: MarketDataProvider, user_id: str = DEFAULT_USER_ID
) -> None:
    """Record one portfolio_snapshots row. Called by the ~30s background
    task in app.main."""
    portfolio = get_portfolio(conn, provider, user_id)
    conn.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) VALUES (?, ?, ?, ?)",
        (str(uuid4()), user_id, portfolio.total_value, _now_iso()),
    )
    conn.commit()


def get_portfolio_history(
    conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID, limit: int = PORTFOLIO_HISTORY_LIMIT
) -> PortfolioHistoryResponse:
    rows = conn.execute(
        "SELECT total_value, recorded_at FROM portfolio_snapshots "
        "WHERE user_id = ? ORDER BY recorded_at ASC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return PortfolioHistoryResponse(
        snapshots=[
            PortfolioSnapshotResponse(total_value=row["total_value"], recorded_at=row["recorded_at"])
            for row in rows
        ]
    )


# --- Routes ---


@router.get("/portfolio", response_model=PortfolioResponse)
def get_portfolio_route(
    conn: sqlite3.Connection = Depends(get_db),
    provider: MarketDataProvider = Depends(get_provider),
) -> PortfolioResponse:
    return get_portfolio(conn, provider)


@router.post("/portfolio/trade", response_model=TradeResponse)
def post_trade_route(
    trade_request: TradeRequest,
    conn: sqlite3.Connection = Depends(get_db),
    provider: MarketDataProvider = Depends(get_provider),
) -> TradeResponse:
    trade = execute_trade(
        conn, provider, trade_request.ticker, trade_request.quantity, trade_request.side
    )
    portfolio = get_portfolio(conn, provider)
    return TradeResponse(trade=trade, portfolio=portfolio)


@router.get("/portfolio/history", response_model=PortfolioHistoryResponse)
def get_portfolio_history_route(
    conn: sqlite3.Connection = Depends(get_db),
) -> PortfolioHistoryResponse:
    return get_portfolio_history(conn)

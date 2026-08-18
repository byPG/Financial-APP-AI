"""Market data routes: SSE price stream + per-ticker history. See
planning/PLAN.md Section 6 and docs/ARCHITECTURE.md Section 5.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from app.db.connection import get_connection
from app.db.schema import DEFAULT_USER_ID
from app.market_data.base import MarketDataProvider
from app.schemas import PriceHistoryResponse, PricePointResponse, PriceUpdateEvent

router = APIRouter(prefix="/api", tags=["prices"])

STREAM_INTERVAL_SECONDS = 0.5


def _change_direction(price: float, previous_price: float) -> str:
    if price > previous_price:
        return "up"
    if price < previous_price:
        return "down"
    return "flat"


def _current_watchlist_tickers() -> list[str]:
    """Reads directly from the DB (not the provider) because the provider
    interface has no "list watched tickers" method — the watchlist table is
    the source of truth for what's "currently watched"
    (docs/ARCHITECTURE.md Section 3)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY ticker",
            (DEFAULT_USER_ID,),
        ).fetchall()
        return [row["ticker"] for row in rows]
    finally:
        conn.close()


async def _price_event_generator(request: Request) -> AsyncIterator[dict]:
    provider: MarketDataProvider = request.app.state.provider
    while True:
        if await request.is_disconnected():
            break
        for ticker in _current_watchlist_tickers():
            snapshot = provider.get_latest(ticker)
            if snapshot is None:
                continue
            event = PriceUpdateEvent(
                ticker=snapshot.ticker,
                price=snapshot.price,
                previous_price=snapshot.previous_price,
                timestamp=snapshot.timestamp,
                change_direction=_change_direction(snapshot.price, snapshot.previous_price),
            )
            yield {"data": event.model_dump_json()}
        await asyncio.sleep(STREAM_INTERVAL_SECONDS)


@router.get("/stream/prices")
async def stream_prices(request: Request) -> EventSourceResponse:
    return EventSourceResponse(_price_event_generator(request))


@router.get("/prices/{ticker}/history", response_model=PriceHistoryResponse)
def get_price_history(ticker: str, request: Request) -> PriceHistoryResponse:
    provider: MarketDataProvider = request.app.state.provider
    ticker = ticker.upper()
    snapshot = provider.get_latest(ticker)
    if snapshot is None:
        raise HTTPException(status_code=404, detail=f"{ticker} is not tracked")
    points = provider.get_history(ticker)
    return PriceHistoryResponse(
        ticker=ticker,
        points=[PricePointResponse(price=p.price, timestamp=p.timestamp) for p in points],
    )

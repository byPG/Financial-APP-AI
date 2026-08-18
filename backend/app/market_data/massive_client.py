"""Massive (Polygon.io) REST polling market data provider. See
docs/ARCHITECTURE.md Section 3 and planning/PLAN.md Section 6.

ASSUMPTION — flagged for correction later: neither planning/PLAN.md nor
docs/ARCHITECTURE.md documents a real Massive API key or response schema (no
sandbox account/docs were available while building this). This implementation
targets Polygon.io's public REST API shape as a best-effort placeholder,
specifically ``GET /v2/last/trade/{ticker}``, which per Polygon's public docs
returns something like:

    {
        "status": "OK",
        "results": {"T": "AAPL", "p": 191.32, "t": 1700000000000000000},
        "request_id": "..."
    }

where ``p`` is the last trade price and ``t`` is a nanosecond-since-epoch
timestamp. All response parsing is isolated in ``_parse_quote_response`` so
it is a single, small place to fix once real Massive API credentials/docs are
available — nothing else in this class depends on the exact shape.

The poll interval is a constructor parameter, not a hardcoded constant:
planning/PLAN.md Section 6 suggests "free tier (5 calls/min): poll every 15
seconds" but flags that figure itself as needing confirmation against current
rate limits, so ``DEFAULT_POLL_INTERVAL_SECONDS`` below is a sensible
starting point, not gospel.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx

from app.market_data.base import MarketDataProvider, PricePoint, PriceSnapshot
from app.market_data.simulator import (
    HISTORY_SAMPLE_INTERVAL_SECONDS,
    HISTORY_WINDOW_SECONDS,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.polygon.io"
DEFAULT_POLL_INTERVAL_SECONDS = 15.0


@dataclass
class _TickerState:
    price: float
    previous_price: float
    timestamp: str
    last_history_sample_at: float
    history: deque[tuple[float, PricePoint]] = field(default_factory=deque)


class MassiveClient(MarketDataProvider):
    """Polls Massive/Polygon.io for the union of watched tickers on an interval."""

    def __init__(
        self,
        api_key: str,
        *,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        base_url: str = DEFAULT_BASE_URL,
        history_sample_interval_seconds: float = HISTORY_SAMPLE_INTERVAL_SECONDS,
        history_window_seconds: float = HISTORY_WINDOW_SECONDS,
        client: httpx.AsyncClient | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._api_key = api_key
        self._poll_interval_seconds = poll_interval_seconds
        self._base_url = base_url.rstrip("/")
        self._history_sample_interval_seconds = history_sample_interval_seconds
        self._history_window_seconds = history_window_seconds
        self._clock = clock or time.time

        # Lazily created if not injected, so instances that never poll (e.g.
        # most unit tests) never open a real network client.
        self._client: httpx.AsyncClient | None = client
        self._owns_client = client is None

        self._watched: set[str] = set()
        self._states: dict[str, _TickerState] = {}
        self._task: asyncio.Task[None] | None = None
        self._running = False

    # --- MarketDataProvider ---

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._running = False
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def watch(self, ticker: str) -> None:
        self._watched.add(ticker.upper())

    def unwatch(self, ticker: str) -> None:
        ticker = ticker.upper()
        self._watched.discard(ticker)
        self._states.pop(ticker, None)

    def get_latest(self, ticker: str) -> PriceSnapshot | None:
        state = self._states.get(ticker.upper())
        if state is None:
            return None
        return PriceSnapshot(
            ticker=ticker.upper(),
            price=state.price,
            previous_price=state.previous_price,
            timestamp=state.timestamp,
        )

    def get_history(self, ticker: str) -> list[PricePoint]:
        state = self._states.get(ticker.upper())
        if state is None:
            return []
        return [point for _, point in state.history]

    # --- internals ---

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def _run_loop(self) -> None:
        while self._running:
            await self.poll_once()
            await asyncio.sleep(self._poll_interval_seconds)

    async def poll_once(self) -> None:
        """Poll every currently-watched ticker once. A failure for one
        ticker (HTTP error, malformed response) is logged and skipped —
        it never aborts the rest of the batch or crashes the poll loop."""
        client = self._get_client()
        for ticker in list(self._watched):
            try:
                response = await client.get(
                    f"{self._base_url}/v2/last/trade/{ticker}",
                    params={"apiKey": self._api_key},
                )
                response.raise_for_status()
                data = response.json()
                price, timestamp_iso = self._parse_quote_response(ticker, data)
            except Exception:
                logger.warning("Massive/Polygon poll failed for %s", ticker, exc_info=True)
                continue

            self._record_price(ticker, price, timestamp_iso)

    def _record_price(self, ticker: str, price: float, timestamp_iso: str) -> None:
        now = self._clock()
        state = self._states.get(ticker)

        if state is None:
            state = _TickerState(
                price=price,
                previous_price=price,
                timestamp=timestamp_iso,
                last_history_sample_at=now,
            )
            state.history.append((now, PricePoint(price=price, timestamp=timestamp_iso)))
            self._states[ticker] = state
            return

        state.previous_price = state.price
        state.price = price
        state.timestamp = timestamp_iso

        if now - state.last_history_sample_at >= self._history_sample_interval_seconds:
            state.history.append((now, PricePoint(price=price, timestamp=timestamp_iso)))
            state.last_history_sample_at = now
            cutoff = now - self._history_window_seconds
            while state.history and state.history[0][0] < cutoff:
                state.history.popleft()

    def _parse_quote_response(self, ticker: str, data: dict) -> tuple[float, str]:
        """Parse one Massive/Polygon.io last-trade response into
        (price, iso_timestamp). See module docstring for the assumed shape —
        deliberately isolated here so it is a single, small place to correct
        once real Massive API docs/credentials are confirmed. Raises
        ValueError on anything unexpected; callers must catch and skip."""
        try:
            results = data["results"]
            price = float(results["p"])
            timestamp_ns = results["t"]
            timestamp_seconds = float(timestamp_ns) / 1_000_000_000.0
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"unexpected Massive/Polygon response shape for {ticker}: {data!r}"
            ) from exc

        if not math.isfinite(price) or price <= 0:
            raise ValueError(f"invalid price for {ticker}: {price!r}")
        if not math.isfinite(timestamp_seconds) or timestamp_seconds <= 0:
            raise ValueError(f"invalid timestamp for {ticker}: {timestamp_ns!r}")

        timestamp_iso = datetime.fromtimestamp(timestamp_seconds, tz=UTC).isoformat()
        return price, timestamp_iso

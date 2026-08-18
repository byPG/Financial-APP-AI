"""In-process market data simulator. See docs/ARCHITECTURE.md Section 3.

Generates prices via geometric Brownian motion (GBM), one independent random
walk per ticker, plus a small shared "group shock" added to tickers in the
same correlation group each tick so related names tend to move together
(planning/PLAN.md Section 6). Occasional larger "event" jumps are layered on
top for drama. No external dependencies — everything lives in memory and is
reset on process restart.
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import random
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from app.market_data.base import MarketDataProvider, PricePoint, PriceSnapshot

# --- Seed prices (planning/PLAN.md Section 15) ---

DEFAULT_SEED_PRICES: dict[str, float] = {
    "AAPL": 190.0,
    "GOOGL": 175.0,
    "MSFT": 420.0,
    "AMZN": 185.0,
    "TSLA": 250.0,
    "NVDA": 130.0,
    "META": 500.0,
    "JPM": 200.0,
    "V": 280.0,
    "NFLX": 630.0,
}

# --- Correlation groups (planning/PLAN.md Section 6) ---
# Tickers sharing a group get one shared random shock added to their return
# each tick, in addition to their own idiosyncratic noise. Deliberately
# simple — a shared scalar factor per group, not a full covariance matrix.
# TSLA and NFLX are intentionally absent so they float independently.
CORRELATION_GROUPS: dict[str, str] = {
    "AAPL": "tech",
    "GOOGL": "tech",
    "MSFT": "tech",
    "AMZN": "tech",
    "NVDA": "tech",
    "META": "tech",
    "JPM": "financials",
    "V": "financials",
}

# --- Timing ---

TICK_INTERVAL_SECONDS = 0.5
HISTORY_SAMPLE_INTERVAL_SECONDS = 12.0  # ~150 points over a 30-minute window
HISTORY_WINDOW_SECONDS = 30 * 60

# Trading-time seconds in a year (252 sessions * 6.5h), used to convert the
# per-tick interval into a "years" fraction for the GBM formula. Using
# trading time rather than wall-clock time keeps volatility realistic at the
# 500ms tick cadence (see test suite for the resulting ~daily-vol sanity check).
SECONDS_PER_YEAR = 252 * 6.5 * 3600

# --- GBM parameters (single shared set across tickers, kept simple) ---

DEFAULT_DRIFT = 0.0
DEFAULT_VOLATILITY = 0.35
GROUP_SHOCK_VOLATILITY = 0.30

# --- Random "event" jumps ---

EVENT_PROBABILITY_PER_TICK = 0.004
EVENT_MIN_PCT = 0.02
EVENT_MAX_PCT = 0.05

_SEED_PRICE_MIN = 20.0
_SEED_PRICE_MAX = 500.0


def _generate_seed_price(ticker: str) -> float:
    """Deterministic, plausible-looking seed price for a ticker with no
    entry in DEFAULT_SEED_PRICES, so newly-watched tickers get a starting
    price immediately. Same ticker always yields the same price."""
    digest = hashlib.sha256(ticker.encode("utf-8")).hexdigest()
    value = int(digest[:8], 16)
    span = _SEED_PRICE_MAX - _SEED_PRICE_MIN
    price = _SEED_PRICE_MIN + (value % 100000) / 100000 * span
    return round(price, 2)


def _iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


@dataclass
class _TickerState:
    price: float
    previous_price: float
    updated_at: float
    last_history_sample_at: float
    history: deque[tuple[float, PricePoint]] = field(default_factory=deque)


class MarketSimulator(MarketDataProvider):
    """GBM-based price simulator with correlated groups and event jumps."""

    def __init__(
        self,
        *,
        tick_interval_seconds: float = TICK_INTERVAL_SECONDS,
        history_sample_interval_seconds: float = HISTORY_SAMPLE_INTERVAL_SECONDS,
        history_window_seconds: float = HISTORY_WINDOW_SECONDS,
        drift: float = DEFAULT_DRIFT,
        volatility: float = DEFAULT_VOLATILITY,
        group_shock_volatility: float = GROUP_SHOCK_VOLATILITY,
        event_probability_per_tick: float = EVENT_PROBABILITY_PER_TICK,
        seed: int | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._tick_interval_seconds = tick_interval_seconds
        self._history_sample_interval_seconds = history_sample_interval_seconds
        self._history_window_seconds = history_window_seconds
        self._drift = drift
        self._volatility = volatility
        self._group_shock_volatility = group_shock_volatility
        self._event_probability_per_tick = event_probability_per_tick
        self._rng = random.Random(seed)
        self._clock = clock or time.time

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

    def watch(self, ticker: str) -> None:
        ticker = ticker.upper()
        if ticker in self._states:
            return
        price = DEFAULT_SEED_PRICES.get(ticker) or _generate_seed_price(ticker)
        now = self._clock()
        state = _TickerState(
            price=price,
            previous_price=price,
            updated_at=now,
            last_history_sample_at=now,
        )
        state.history.append((now, PricePoint(price=price, timestamp=_iso(now))))
        self._states[ticker] = state

    def unwatch(self, ticker: str) -> None:
        self._states.pop(ticker.upper(), None)

    def get_latest(self, ticker: str) -> PriceSnapshot | None:
        state = self._states.get(ticker.upper())
        if state is None:
            return None
        return PriceSnapshot(
            ticker=ticker.upper(),
            price=state.price,
            previous_price=state.previous_price,
            timestamp=_iso(state.updated_at),
        )

    def get_history(self, ticker: str) -> list[PricePoint]:
        state = self._states.get(ticker.upper())
        if state is None:
            return []
        return [point for _, point in state.history]

    # --- internals ---

    async def _run_loop(self) -> None:
        try:
            while self._running:
                self._tick()
                await asyncio.sleep(self._tick_interval_seconds)
        except asyncio.CancelledError:
            raise

    def _tick(self) -> None:
        """Advance every watched ticker by one simulated tick. Synchronous
        and side-effect-only on internal state, so tests can drive it
        directly and deterministically without waiting on real sleeps."""
        if not self._states:
            return

        now = self._clock()
        dt_years = self._tick_interval_seconds / SECONDS_PER_YEAR
        sqrt_dt = math.sqrt(dt_years)

        group_shocks: dict[str, float] = {
            group: self._rng.gauss(0.0, 1.0) for group in set(CORRELATION_GROUPS.values())
        }

        for ticker, state in self._states.items():
            idiosyncratic_z = self._rng.gauss(0.0, 1.0)
            group = CORRELATION_GROUPS.get(ticker)
            group_component = 0.0
            if group is not None:
                group_component = self._group_shock_volatility * sqrt_dt * group_shocks[group]

            log_return = (
                (self._drift - 0.5 * self._volatility**2) * dt_years
                + self._volatility * sqrt_dt * idiosyncratic_z
                + group_component
            )

            if self._rng.random() < self._event_probability_per_tick:
                event_pct = self._rng.uniform(EVENT_MIN_PCT, EVENT_MAX_PCT)
                if self._rng.random() < 0.5:
                    event_pct = -event_pct
                log_return += math.log(1.0 + event_pct)

            new_price = max(state.price * math.exp(log_return), 0.01)

            state.previous_price = state.price
            state.price = new_price
            state.updated_at = now

            if now - state.last_history_sample_at >= self._history_sample_interval_seconds:
                state.history.append((now, PricePoint(price=new_price, timestamp=_iso(now))))
                state.last_history_sample_at = now
                cutoff = now - self._history_window_seconds
                while state.history and state.history[0][0] < cutoff:
                    state.history.popleft()

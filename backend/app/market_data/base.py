"""Abstract market data provider interface. See docs/ARCHITECTURE.md, Section 3.

Both the simulator (simulator.py) and the Massive API client (massive_client.py)
implement this. Backend code depends only on MarketDataProvider, never on a
concrete implementation, so the two are interchangeable via the
MASSIVE_API_KEY environment variable (planning/PLAN.md Section 5).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class PriceSnapshot:
    """The latest known price for a ticker, as held in the price cache."""

    ticker: str
    price: float
    previous_price: float
    timestamp: str  # ISO 8601


@dataclass(frozen=True)
class PricePoint:
    """One downsampled point in a ticker's ~30-minute price history."""

    price: float
    timestamp: str  # ISO 8601


class MarketDataProvider(ABC):
    @abstractmethod
    async def start(self) -> None:
        """Start the background task that keeps prices updating."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the background task."""

    @abstractmethod
    def watch(self, ticker: str) -> None:
        """Start tracking a ticker. Called when it's added to the watchlist."""

    @abstractmethod
    def unwatch(self, ticker: str) -> None:
        """Stop tracking a ticker. Called when it's removed from the watchlist."""

    @abstractmethod
    def get_latest(self, ticker: str) -> PriceSnapshot | None:
        """Return the latest cached price for a ticker, or None if not tracked."""

    @abstractmethod
    def get_history(self, ticker: str) -> list[PricePoint]:
        """Return the downsampled ~30-minute price history for a ticker."""

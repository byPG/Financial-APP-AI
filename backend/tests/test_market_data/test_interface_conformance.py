"""Shared conformance tests run against both MarketDataProvider
implementations, so it's structurally obvious both honor the abstract
interface defined in app/market_data/base.py (the Architect's contract).

Only asserts behavior guaranteed by the interface itself. Provider-specific
behavior (e.g. the simulator seeding an immediate price on watch(), vs.
MassiveClient needing a poll first) is covered in each provider's own test
module, not here.
"""

from __future__ import annotations

import asyncio

import pytest

from app.market_data.base import MarketDataProvider
from app.market_data.massive_client import MassiveClient
from app.market_data.simulator import MarketSimulator


def _make_simulator() -> MarketDataProvider:
    return MarketSimulator(seed=1)


def _make_massive_client() -> MarketDataProvider:
    return MassiveClient(api_key="test-key")


PROVIDER_FACTORIES = [_make_simulator, _make_massive_client]
PROVIDER_IDS = ["simulator", "massive_client"]


@pytest.mark.parametrize("make_provider", PROVIDER_FACTORIES, ids=PROVIDER_IDS)
def test_is_a_market_data_provider(make_provider):
    provider = make_provider()
    assert isinstance(provider, MarketDataProvider)


@pytest.mark.parametrize("make_provider", PROVIDER_FACTORIES, ids=PROVIDER_IDS)
def test_untracked_ticker_yields_no_snapshot_and_empty_history(make_provider):
    provider = make_provider()
    assert provider.get_latest("NFLX") is None
    assert provider.get_history("NFLX") == []


@pytest.mark.parametrize("make_provider", PROVIDER_FACTORIES, ids=PROVIDER_IDS)
def test_unwatch_removes_tracking(make_provider):
    provider = make_provider()
    provider.watch("AAPL")
    provider.unwatch("AAPL")
    assert provider.get_latest("AAPL") is None
    assert provider.get_history("AAPL") == []


@pytest.mark.parametrize("make_provider", PROVIDER_FACTORIES, ids=PROVIDER_IDS)
def test_unwatch_of_never_watched_ticker_is_a_safe_noop(make_provider):
    provider = make_provider()
    provider.unwatch("DOESNOTEXIST")  # must not raise
    assert provider.get_latest("DOESNOTEXIST") is None


@pytest.mark.parametrize("make_provider", PROVIDER_FACTORIES, ids=PROVIDER_IDS)
def test_get_history_returns_a_list(make_provider):
    provider = make_provider()
    provider.watch("AAPL")
    assert isinstance(provider.get_history("AAPL"), list)


@pytest.mark.asyncio
@pytest.mark.parametrize("make_provider", PROVIDER_FACTORIES, ids=PROVIDER_IDS)
async def test_start_and_stop_do_not_raise(make_provider):
    # Bounded with a timeout: MassiveClient's loop polls immediately on
    # start(), which (with no respx mock active here) would hit the real
    # network — cancellation should abort that promptly, but the timeout
    # guarantees the test can't hang if it doesn't.
    provider = make_provider()
    provider.watch("AAPL")
    await provider.start()
    await asyncio.wait_for(provider.stop(), timeout=5.0)

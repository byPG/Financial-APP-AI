"""Unit tests for app.market_data.massive_client.MassiveClient.

Response parsing is mocked with `respx` (an httpx-native request mocking
library) rather than hitting the network. respx was added as a dev
dependency for this — see backend/pyproject.toml — because httpx is the HTTP
client this class is built on, and respx intercepts at the transport layer,
so `MassiveClient`'s internally-created `httpx.AsyncClient` gets mocked
without any production code changes (no client injection required, though
the class supports that too for other tests here).
"""

from __future__ import annotations

import httpx
import pytest
import respx

from app.market_data.massive_client import MassiveClient

from ._fake_clock import FakeClock

VALID_RESPONSE = {
    "status": "OK",
    "results": {"T": "AAPL", "p": 191.32, "t": 1_700_000_000_000_000_000},
    "request_id": "abc123",
}


# --- _parse_quote_response ---


def test_parse_quote_response_valid():
    client = MassiveClient(api_key="test-key")
    price, timestamp_iso = client._parse_quote_response("AAPL", VALID_RESPONSE)

    assert price == 191.32
    assert timestamp_iso.startswith("2023-11-14")  # 1.7e18 ns epoch -> mid-Nov 2023


@pytest.mark.parametrize(
    "bad_response",
    [
        {},
        {"results": {}},
        {"results": {"p": "not-a-number", "t": 1_700_000_000_000_000_000}},
        {"results": {"p": 191.32, "t": "not-a-number"}},
        {"results": {"p": -5.0, "t": 1_700_000_000_000_000_000}},
        {"results": {"p": 191.32, "t": -1}},
        {"results": None},
        "not-a-dict-at-all",
    ],
)
def test_parse_quote_response_rejects_malformed_shapes(bad_response):
    client = MassiveClient(api_key="test-key")
    with pytest.raises(ValueError):
        # bad_response deliberately includes non-dict cases to exercise the
        # defensive except clause around subscripting/float conversion.
        client._parse_quote_response("AAPL", bad_response)  # type: ignore[arg-type]


# --- watch/unwatch/get_latest/get_history contract ---


def test_get_latest_is_none_before_any_poll():
    client = MassiveClient(api_key="test-key")
    client.watch("AAPL")
    assert client.get_latest("AAPL") is None
    assert client.get_history("AAPL") == []


def test_unwatch_stops_tracking():
    client = MassiveClient(api_key="test-key")
    client.watch("AAPL")
    client.unwatch("AAPL")
    assert client.get_latest("AAPL") is None


# --- poll_once ---


@pytest.mark.asyncio
@respx.mock
async def test_poll_once_updates_cache_on_success():
    respx.get("https://api.polygon.io/v2/last/trade/AAPL").mock(
        return_value=httpx.Response(200, json=VALID_RESPONSE)
    )

    client = MassiveClient(api_key="test-key")
    client.watch("AAPL")
    await client.poll_once()

    snapshot = client.get_latest("AAPL")
    assert snapshot is not None
    assert snapshot.price == 191.32
    assert snapshot.ticker == "AAPL"

    history = client.get_history("AAPL")
    assert len(history) == 1

    await client.stop()


@pytest.mark.asyncio
@respx.mock
async def test_poll_once_skips_failed_ticker_without_crashing():
    respx.get("https://api.polygon.io/v2/last/trade/AAPL").mock(
        return_value=httpx.Response(200, json={"unexpected": "shape"})
    )
    respx.get("https://api.polygon.io/v2/last/trade/MSFT").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "OK",
                "results": {"T": "MSFT", "p": 420.5, "t": 1_700_000_000_000_000_000},
            },
        )
    )

    client = MassiveClient(api_key="test-key")
    client.watch("AAPL")
    client.watch("MSFT")

    await client.poll_once()  # must not raise despite AAPL's bad response

    assert client.get_latest("AAPL") is None
    msft_snapshot = client.get_latest("MSFT")
    assert msft_snapshot is not None
    assert msft_snapshot.price == 420.5

    await client.stop()


@pytest.mark.asyncio
@respx.mock
async def test_poll_once_skips_ticker_on_http_error():
    respx.get("https://api.polygon.io/v2/last/trade/AAPL").mock(
        return_value=httpx.Response(500)
    )

    client = MassiveClient(api_key="test-key")
    client.watch("AAPL")

    await client.poll_once()  # must not raise on a 500

    assert client.get_latest("AAPL") is None

    await client.stop()


# --- history downsampling (mirrors the simulator's contract) ---


def test_history_downsampling_cadence_and_window():
    clock = FakeClock()
    client = MassiveClient(
        api_key="test-key",
        history_sample_interval_seconds=12.0,
        history_window_seconds=60.0,
        clock=clock,
    )

    client._record_price("AAPL", 100.0, "2024-01-01T00:00:00+00:00")
    assert len(client.get_history("AAPL")) == 1

    clock.advance(5.0)
    client._record_price("AAPL", 100.5, "2024-01-01T00:00:05+00:00")
    assert len(client.get_history("AAPL")) == 1  # only 5s elapsed

    clock.advance(8.0)  # total 13s elapsed since last sample
    client._record_price("AAPL", 101.0, "2024-01-01T00:00:13+00:00")
    assert len(client.get_history("AAPL")) == 2

    # Advance well past the 60s window with repeated 12s-cadence samples and
    # confirm old points get trimmed rather than accumulating forever.
    for i in range(10):
        clock.advance(12.0)
        client._record_price("AAPL", 101.0 + i, f"point-{i}")

    history = client.get_history("AAPL")
    assert len(history) <= 6

"""Unit tests for app.market_data.simulator.MarketSimulator.

Covers: seed prices, plausible seed generation for unknown tickers, GBM
sanity (positivity, finiteness, roughly correct volatility magnitude),
correlated movement within a group vs. across groups, occasional event
jumps, watch/unwatch tracking, and history downsampling cadence/window.
"""

from __future__ import annotations

import math
import statistics

from app.market_data.base import PriceSnapshot
from app.market_data.simulator import (
    DEFAULT_SEED_PRICES,
    DEFAULT_VOLATILITY,
    SECONDS_PER_YEAR,
    TICK_INTERVAL_SECONDS,
    MarketSimulator,
    _generate_seed_price,
)

from ._fake_clock import FakeClock


# --- seed prices ---


def test_default_seed_prices_match_plan_table():
    expected = {
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
    assert DEFAULT_SEED_PRICES == expected


def test_watch_uses_default_seed_price_for_known_ticker():
    sim = MarketSimulator()
    sim.watch("AAPL")
    snapshot = sim.get_latest("AAPL")
    assert isinstance(snapshot, PriceSnapshot)
    assert snapshot.price == 190.0
    assert snapshot.previous_price == 190.0


def test_unknown_ticker_gets_a_plausible_deterministic_seed_price():
    price_a = _generate_seed_price("ZZZZ")
    price_b = _generate_seed_price("ZZZZ")
    price_c = _generate_seed_price("QQXY")

    assert 20.0 <= price_a <= 500.0
    assert price_a == price_b  # deterministic for the same ticker
    assert price_a != price_c  # different tickers get different prices


def test_watch_generates_seed_price_for_unlisted_ticker():
    sim = MarketSimulator()
    sim.watch("ZVZZ")
    snapshot = sim.get_latest("ZVZZ")
    assert snapshot is not None
    assert 20.0 <= snapshot.price <= 500.0


# --- watch / unwatch tracking ---


def test_get_latest_returns_none_for_untracked_ticker():
    sim = MarketSimulator()
    assert sim.get_latest("AAPL") is None


def test_get_history_returns_empty_list_for_untracked_ticker():
    sim = MarketSimulator()
    assert sim.get_history("AAPL") == []


def test_unwatch_stops_tracking():
    sim = MarketSimulator()
    sim.watch("AAPL")
    assert sim.get_latest("AAPL") is not None

    sim.unwatch("AAPL")
    assert sim.get_latest("AAPL") is None
    assert sim.get_history("AAPL") == []


def test_watch_is_idempotent_and_ticker_case_insensitive():
    sim = MarketSimulator()
    sim.watch("aapl")
    first = sim.get_latest("AAPL")
    sim.watch("AAPL")  # already tracked, must not reset the price
    second = sim.get_latest("aapl")
    assert first == second


# --- GBM sanity ---


def test_prices_stay_positive_and_finite_after_many_ticks():
    sim = MarketSimulator(seed=7)
    tickers = list(DEFAULT_SEED_PRICES.keys())
    for t in tickers:
        sim.watch(t)

    for _ in range(3000):
        sim._tick()

    for t in tickers:
        snap = sim.get_latest(t)
        assert snap is not None
        assert snap.price > 0
        assert math.isfinite(snap.price)
        assert math.isfinite(snap.previous_price)


def test_pure_diffusion_return_stdev_is_right_order_of_magnitude():
    # Isolate idiosyncratic diffusion only: no group (TSLA is ungrouped) and
    # no event jumps, so the observed stdev of per-tick log returns should
    # track the theoretical GBM diffusion term volatility * sqrt(dt).
    sim = MarketSimulator(seed=123, event_probability_per_tick=0.0)
    sim.watch("TSLA")

    returns: list[float] = []
    for _ in range(4000):
        sim._tick()
        snap = sim.get_latest("TSLA")
        returns.append(math.log(snap.price / snap.previous_price))

    observed_stdev = statistics.pstdev(returns)

    dt_years = TICK_INTERVAL_SECONDS / SECONDS_PER_YEAR
    expected_stdev = DEFAULT_VOLATILITY * math.sqrt(dt_years)

    assert expected_stdev / 3 < observed_stdev < expected_stdev * 3


def test_events_occasionally_produce_a_much_bigger_jump():
    # event_probability_per_tick=1.0 forces every tick to include an event;
    # its magnitude (2-5%) dwarfs the diffusion term, so the resulting log
    # return should clearly exceed ordinary diffusion noise.
    sim = MarketSimulator(seed=99, event_probability_per_tick=1.0)
    sim.watch("TSLA")

    sim._tick()
    snap = sim.get_latest("TSLA")
    log_return = math.log(snap.price / snap.previous_price)

    assert abs(log_return) > 0.01  # diffusion-only noise is ~1e-4 at this cadence


def test_events_are_rare_at_default_probability():
    sim = MarketSimulator(seed=5)
    sim.watch("TSLA")

    big_moves = 0
    for _ in range(5000):
        sim._tick()
        snap = sim.get_latest("TSLA")
        if abs(math.log(snap.price / snap.previous_price)) > 0.01:
            big_moves += 1

    # Expected ~20 events in 5000 ticks at p=0.004 (P[zero events] ~ e^-20,
    # negligible regardless of seed); assert it's "occasional", not on every
    # tick and not (essentially) never.
    assert 0 < big_moves < 500


# --- correlation ---


def test_same_group_tickers_are_more_correlated_than_cross_group():
    sim = MarketSimulator(seed=42, event_probability_per_tick=0.0)
    for t in ("AAPL", "MSFT", "TSLA"):
        sim.watch(t)

    returns: dict[str, list[float]] = {"AAPL": [], "MSFT": [], "TSLA": []}
    for _ in range(3000):
        sim._tick()
        for t in returns:
            snap = sim.get_latest(t)
            returns[t].append(math.log(snap.price / snap.previous_price))

    corr_same_group = statistics.correlation(returns["AAPL"], returns["MSFT"])
    corr_cross_group = statistics.correlation(returns["AAPL"], returns["TSLA"])

    assert corr_same_group > 0.25
    assert corr_same_group > corr_cross_group
    assert abs(corr_cross_group) < 0.2


# --- history downsampling ---


def test_history_has_one_point_immediately_after_watch():
    clock = FakeClock()
    sim = MarketSimulator(clock=clock)
    sim.watch("AAPL")
    assert len(sim.get_history("AAPL")) == 1


def test_history_does_not_sample_before_cadence_elapses():
    clock = FakeClock()
    sim = MarketSimulator(history_sample_interval_seconds=12.0, clock=clock)
    sim.watch("AAPL")

    for _ in range(10):
        clock.advance(1.0)
        sim._tick()

    assert len(sim.get_history("AAPL")) == 1  # only 10s elapsed


def test_history_samples_once_cadence_elapses():
    clock = FakeClock()
    sim = MarketSimulator(history_sample_interval_seconds=12.0, clock=clock)
    sim.watch("AAPL")

    for _ in range(11):
        clock.advance(1.0)
        sim._tick()  # 11s elapsed, no sample yet
    assert len(sim.get_history("AAPL")) == 1

    clock.advance(2.0)
    sim._tick()  # 13s elapsed, crosses the 12s cadence
    assert len(sim.get_history("AAPL")) == 2


def test_history_window_trims_old_points():
    clock = FakeClock()
    sim = MarketSimulator(
        history_sample_interval_seconds=1.0,
        history_window_seconds=5.0,
        clock=clock,
    )
    sim.watch("AAPL")

    for _ in range(20):
        clock.advance(1.0)
        sim._tick()

    history = sim.get_history("AAPL")
    # 5s window with 1s spacing => at most ~6 points, never anywhere near 20
    assert 1 <= len(history) <= 7

"""Portfolio business logic tests: trade execution, P&L math, avg-cost
accounting. Most of these call app.portfolio's functions directly against
an isolated db_conn + an unstarted MarketSimulator (deterministic: no
background tick loop running, so prices only change when a test explicitly
mutates them). API-level tests cover the same rules through the HTTP layer
(status codes, response shapes).
"""

from __future__ import annotations

import pytest

from app.errors import ValidationError
from app.portfolio import execute_trade, get_portfolio


def test_buy_success(db_conn, provider):
    provider.watch("AAPL")  # seed price 190.0, see simulator.DEFAULT_SEED_PRICES

    trade = execute_trade(db_conn, provider, "AAPL", 10, "buy")

    assert trade.ticker == "AAPL"
    assert trade.side == "buy"
    assert trade.quantity == 10
    assert trade.price == pytest.approx(190.0)

    portfolio = get_portfolio(db_conn, provider)
    assert portfolio.cash_balance == pytest.approx(10000.0 - 1900.0)
    assert len(portfolio.positions) == 1
    position = portfolio.positions[0]
    assert position.ticker == "AAPL"
    assert position.quantity == 10
    assert position.avg_cost == pytest.approx(190.0)


def test_sell_success(db_conn, provider):
    provider.watch("AAPL")
    execute_trade(db_conn, provider, "AAPL", 10, "buy")

    trade = execute_trade(db_conn, provider, "AAPL", 4, "sell")

    assert trade.side == "sell"
    assert trade.quantity == 4

    portfolio = get_portfolio(db_conn, provider)
    assert portfolio.cash_balance == pytest.approx(10000.0 - 1900.0 + 4 * 190.0)
    assert len(portfolio.positions) == 1
    assert portfolio.positions[0].quantity == 6


def test_buy_insufficient_cash_raises(db_conn, provider):
    provider.watch("AAPL")  # price 190.0, cash 10000 -> max ~52 shares

    with pytest.raises(ValidationError, match="insufficient cash"):
        execute_trade(db_conn, provider, "AAPL", 1000, "buy")

    # no partial application
    portfolio = get_portfolio(db_conn, provider)
    assert portfolio.cash_balance == pytest.approx(10000.0)
    assert portfolio.positions == []


def test_sell_insufficient_shares_raises(db_conn, provider):
    provider.watch("AAPL")

    with pytest.raises(ValidationError, match="insufficient shares"):
        execute_trade(db_conn, provider, "AAPL", 5, "sell")


def test_sell_more_than_owned_raises(db_conn, provider):
    provider.watch("AAPL")
    execute_trade(db_conn, provider, "AAPL", 5, "buy")

    with pytest.raises(ValidationError, match="insufficient shares"):
        execute_trade(db_conn, provider, "AAPL", 6, "sell")


def test_trade_ticker_not_on_watchlist_raises(db_conn, provider):
    # never watched -> provider.get_latest returns None
    with pytest.raises(ValidationError, match="not on the watchlist"):
        execute_trade(db_conn, provider, "IBM", 1, "buy")


def test_trade_invalid_ticker_format_raises(db_conn, provider):
    with pytest.raises(ValidationError, match="invalid ticker format"):
        execute_trade(db_conn, provider, "TOOLONG", 1, "buy")


def test_position_deleted_at_zero_quantity(db_conn, provider):
    provider.watch("AAPL")
    execute_trade(db_conn, provider, "AAPL", 10, "buy")
    execute_trade(db_conn, provider, "AAPL", 10, "sell")

    row = db_conn.execute(
        "SELECT * FROM positions WHERE ticker = 'AAPL'"
    ).fetchone()
    assert row is None

    portfolio = get_portfolio(db_conn, provider)
    assert portfolio.positions == []
    assert portfolio.cash_balance == pytest.approx(10000.0)


def test_avg_cost_recalculated_across_multiple_buys(db_conn, provider):
    provider.watch("AAPL")
    execute_trade(db_conn, provider, "AAPL", 10, "buy")  # @ 190.0

    # Directly mutate the simulator's internal price to simulate a tick
    # between trades — deterministic and avoids depending on the async
    # background loop / real time passing in a unit test.
    provider._states["AAPL"].price = 210.0

    execute_trade(db_conn, provider, "AAPL", 10, "buy")  # @ 210.0

    portfolio = get_portfolio(db_conn, provider)
    assert len(portfolio.positions) == 1
    position = portfolio.positions[0]
    assert position.quantity == 20
    # weighted avg: (10*190 + 10*210) / 20 = 200
    assert position.avg_cost == pytest.approx(200.0)


def test_unrealized_pnl_math(db_conn, provider):
    provider.watch("AAPL")
    execute_trade(db_conn, provider, "AAPL", 10, "buy")  # @ 190.0

    provider._states["AAPL"].price = 209.0  # +10%

    portfolio = get_portfolio(db_conn, provider)
    position = portfolio.positions[0]
    assert position.current_price == pytest.approx(209.0)
    assert position.unrealized_pnl == pytest.approx((209.0 - 190.0) * 10)
    assert position.unrealized_pnl_pct == pytest.approx(10.0)
    assert portfolio.total_unrealized_pnl == pytest.approx((209.0 - 190.0) * 10)
    assert portfolio.total_value == pytest.approx(portfolio.cash_balance + 209.0 * 10)


def test_buy_then_sell_updates_cash_atomically(db_conn, provider):
    provider.watch("AAPL")
    trade = execute_trade(db_conn, provider, "AAPL", 5, "buy")
    cash_row = db_conn.execute(
        "SELECT cash_balance FROM users_profile WHERE id = 'default'"
    ).fetchone()
    assert cash_row["cash_balance"] == pytest.approx(10000.0 - trade.price * 5)

    trade_row = db_conn.execute(
        "SELECT COUNT(*) AS n FROM trades WHERE ticker = 'AAPL'"
    ).fetchone()
    assert trade_row["n"] == 1


# --- API-level tests (status codes, response shapes) ---


def test_api_trade_buy_and_sell_roundtrip(client):
    watchlist = client.get("/api/watchlist").json()
    ticker = watchlist["items"][0]["ticker"]

    buy_resp = client.post("/api/portfolio/trade", json={"ticker": ticker, "quantity": 1, "side": "buy"})
    assert buy_resp.status_code == 200
    body = buy_resp.json()
    assert body["trade"]["ticker"] == ticker
    assert body["trade"]["side"] == "buy"
    assert len(body["portfolio"]["positions"]) == 1

    sell_resp = client.post("/api/portfolio/trade", json={"ticker": ticker, "quantity": 1, "side": "sell"})
    assert sell_resp.status_code == 200
    assert sell_resp.json()["portfolio"]["positions"] == []


def test_api_trade_ticker_not_on_watchlist_400(client):
    resp = client.post("/api/portfolio/trade", json={"ticker": "IBM", "quantity": 1, "side": "buy"})
    assert resp.status_code == 400
    assert "detail" in resp.json()


def test_api_trade_insufficient_cash_400(client):
    watchlist = client.get("/api/watchlist").json()
    ticker = watchlist["items"][0]["ticker"]
    resp = client.post(
        "/api/portfolio/trade", json={"ticker": ticker, "quantity": 1_000_000, "side": "buy"}
    )
    assert resp.status_code == 400


def test_api_portfolio_history_returns_list(client):
    resp = client.get("/api/portfolio/history")
    assert resp.status_code == 200
    assert "snapshots" in resp.json()

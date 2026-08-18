"""Chat / LLM_MOCK=true tests. See planning/REVIEW.md item 14 and
planning/PLAN.md Section 9.

All tests here run with LLM_MOCK=true (set by the db_path fixture in
conftest.py) so nothing hits the network — this is required by the task,
not just convenient.
"""

from __future__ import annotations

from app.chat import _find_ticker_in_message, _mock_llm_response
from app.schemas import WatchlistItemResponse, WatchlistResponse


def test_find_ticker_in_message_finds_uppercase_word():
    assert _find_ticker_in_message("please buy AAPL now") == "AAPL"


def test_find_ticker_in_message_ignores_lowercase():
    assert _find_ticker_in_message("please buy apple now") is None


def test_mock_llm_buy_with_ticker_in_message():
    watchlist = WatchlistResponse(items=[])
    result = _mock_llm_response("buy AAPL", watchlist)
    assert len(result.trades) == 1
    assert result.trades[0].ticker == "AAPL"
    assert result.trades[0].side == "buy"
    assert result.trades[0].quantity == 1


def test_mock_llm_buy_without_ticker_defaults_to_first_watchlist_item():
    watchlist = WatchlistResponse(
        items=[
            WatchlistItemResponse(
                ticker="TSLA", added_at="x", current_price=1.0, previous_price=1.0
            )
        ]
    )
    result = _mock_llm_response("please buy some shares", watchlist)
    assert result.trades[0].ticker == "TSLA"


def test_mock_llm_watch_intent_produces_watchlist_change():
    watchlist = WatchlistResponse(items=[])
    result = _mock_llm_response("please watch NFLX for me", watchlist)
    assert len(result.watchlist_changes) == 1
    assert result.watchlist_changes[0].ticker == "NFLX"
    assert result.watchlist_changes[0].action == "add"


def test_mock_llm_generic_message_has_no_actions():
    watchlist = WatchlistResponse(items=[])
    result = _mock_llm_response("how is my portfolio doing?", watchlist)
    assert result.trades == []
    assert result.watchlist_changes == []
    assert result.message


# --- API-level end-to-end tests ---


def test_api_chat_buy_executes_real_trade(client):
    watchlist = client.get("/api/watchlist").json()
    ticker = watchlist["items"][0]["ticker"]

    resp = client.post("/api/chat", json={"message": f"buy {ticker}"})
    assert resp.status_code == 200
    body = resp.json()

    assert body["message"]["role"] == "assistant"
    assert body["message"]["actions"] is not None
    assert len(body["message"]["actions"]["trades"]) == 1
    trade_action = body["message"]["actions"]["trades"][0]
    assert trade_action["ticker"] == ticker
    assert trade_action["status"] == "executed"

    # portfolio in the response reflects the trade
    assert len(body["portfolio"]["positions"]) == 1
    assert body["portfolio"]["positions"][0]["ticker"] == ticker

    # and it's really persisted / reflected via the portfolio endpoint too
    portfolio_resp = client.get("/api/portfolio").json()
    assert len(portfolio_resp["positions"]) == 1


def test_api_chat_watch_executes_watchlist_change(client):
    resp = client.post("/api/chat", json={"message": "watch PYPL please"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"]["actions"]["watchlist_changes"][0]["ticker"] == "PYPL"
    assert body["message"]["actions"]["watchlist_changes"][0]["status"] == "executed"

    watchlist_resp = client.get("/api/watchlist").json()
    tickers = {item["ticker"] for item in watchlist_resp["items"]}
    assert "PYPL" in tickers


def test_api_chat_generic_message_has_null_actions(client):
    resp = client.post("/api/chat", json={"message": "how am I doing?"})
    assert resp.status_code == 200
    assert resp.json()["message"]["actions"] is None


def test_api_chat_history_persists_and_is_returned_oldest_first(client):
    client.post("/api/chat", json={"message": "hello"})
    client.post("/api/chat", json={"message": "how am I doing?"})

    resp = client.get("/api/chat")
    assert resp.status_code == 200
    messages = resp.json()["messages"]

    # 2 user + 2 assistant = 4 messages, oldest first
    assert len(messages) == 4
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "hello"
    assert messages[1]["role"] == "assistant"
    assert messages[2]["content"] == "how am I doing?"


def test_api_chat_failed_trade_reports_error_in_actions(client):
    # "IBM" is not on the default watchlist, so the mock's buy instruction
    # will fail validation inside execute_trade -> status "failed" with an
    # error message, not a 500.
    resp = client.post("/api/chat", json={"message": "buy IBM"})
    assert resp.status_code == 200
    body = resp.json()
    trade_action = body["message"]["actions"]["trades"][0]
    assert trade_action["status"] == "failed"
    assert trade_action["error"]

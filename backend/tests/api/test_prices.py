"""GET /api/prices/{ticker}/history tests."""

from __future__ import annotations


def test_price_history_for_watched_ticker(client):
    watchlist = client.get("/api/watchlist").json()
    ticker = watchlist["items"][0]["ticker"]

    resp = client.get(f"/api/prices/{ticker}/history")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == ticker
    assert isinstance(body["points"], list)


def test_price_history_404_for_untracked_ticker(client):
    resp = client.get("/api/prices/ZZZZZ/history")
    assert resp.status_code == 404

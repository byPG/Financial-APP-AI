"""Shared ticker-format validation. See planning/PLAN.md Section 14 (Ticker
Scope) and docs/ARCHITECTURE.md Section 4 — the sole validity rule for a
ticker symbol anywhere in the app is ``^[A-Z]{1,5}$``.

Used by watchlist.py (POST /api/watchlist), portfolio.py (POST
/api/portfolio/trade — schemas.TradeRequest.ticker has no pattern constraint
at the Pydantic level, so this must be checked manually), and chat.py (both
for validating LLM-issued instructions and for parsing tickers out of mock
LLM keyword matching).
"""

from __future__ import annotations

import re

TICKER_PATTERN = re.compile(r"^[A-Z]{1,5}$")


def is_valid_ticker(ticker: str) -> bool:
    return bool(TICKER_PATTERN.match(ticker))

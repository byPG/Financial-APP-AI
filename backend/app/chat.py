"""Chat / LLM integration + the /api/chat routes. See planning/PLAN.md
Section 9 (as finalized by planning/REVIEW.md items 11/12/14/21/23) and
docs/ARCHITECTURE.md Section 4.

Transport: single JSON request/response, no SSE/chunking — the backend
calls the LLM once, waits for the complete structured response, executes
any trades/watchlist changes, persists the message, and returns the
finished text. The frontend does its own client-side typewriter effect.

Trust boundary (planning/REVIEW.md item 18): the LLM's structured output is
untrusted input, exactly like any other request body. Every trade/watchlist
instruction it returns is executed through the *same* validated functions
(portfolio.execute_trade, watchlist.add_ticker/remove_ticker) the manual
REST endpoints use — never a shortcut path.
"""

from __future__ import annotations

import logging
import os
import re
import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.db.schema import DEFAULT_USER_ID
from app.deps import get_db, get_provider
from app.errors import DomainError
from app.market_data.base import MarketDataProvider
from app.portfolio import execute_trade, get_portfolio
from app.schemas import (
    ChatActions,
    ChatHistoryResponse,
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    LLMStructuredResponse,
    LLMTradeInstruction,
    LLMWatchlistInstruction,
    PortfolioResponse,
    TradeAction,
    WatchlistChangeAction,
    WatchlistResponse,
)
from app.tickers import TICKER_PATTERN
from app.watchlist import add_ticker, list_watchlist, remove_ticker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

# deepseek/deepseek-chat-v3.1:free was retired from OpenRouter's free tier
# (now paid-only); google/gemma-4-26b-a4b-it:free is a currently-free
# alternative confirmed to support structured JSON outputs.
MODEL = "openrouter/google/gemma-4-26b-a4b-it:free"

# How many prior messages (both roles) to include as conversation history
# when calling the LLM. Small on purpose — this is a simulated single-user
# app, not a long-running support thread.
CHAT_HISTORY_CONTEXT_LIMIT = 20

# What GET /api/chat returns to repopulate the panel on page load.
CHAT_HISTORY_RESPONSE_LIMIT = 100

# Fallback ticker for the mock "watch"/"add" intent when the user's message
# doesn't contain an uppercase ticker-shaped word — taken from
# planning/PLAN.md Section 9's own structured-output example.
DEFAULT_MOCK_WATCH_TICKER = "PYPL"

_WORD_RE = re.compile(r"[A-Za-z]+")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _is_mock_mode() -> bool:
    return os.environ.get("LLM_MOCK", "false").strip().lower() == "true"


def _row_to_message(row: sqlite3.Row) -> ChatMessageResponse:
    actions = None
    if row["actions"]:
        actions = ChatActions.model_validate_json(row["actions"])
    return ChatMessageResponse(
        id=row["id"],
        role=row["role"],
        content=row["content"],
        actions=actions,
        created_at=row["created_at"],
    )


def get_chat_history(
    conn: sqlite3.Connection,
    user_id: str = DEFAULT_USER_ID,
    limit: int = CHAT_HISTORY_RESPONSE_LIMIT,
) -> ChatHistoryResponse:
    rows = conn.execute(
        "SELECT id, role, content, actions, created_at FROM chat_messages "
        "WHERE user_id = ? ORDER BY created_at ASC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return ChatHistoryResponse(messages=[_row_to_message(row) for row in rows])


# --- Mock LLM (LLM_MOCK=true) ---


def _find_ticker_in_message(message: str) -> str | None:
    """First uppercase, ticker-shaped word in the raw (not lowercased)
    message, e.g. "buy AAPL" -> "AAPL". Returns None if there isn't one."""
    for word in _WORD_RE.findall(message):
        if TICKER_PATTERN.match(word):
            return word
    return None


def _mock_llm_response(message: str, watchlist: WatchlistResponse) -> LLMStructuredResponse:
    """Deterministic keyword-matched mock, per planning/REVIEW.md item 14:
    - "buy" -> buy 1 share of a ticker parsed from the message, else the
      first watchlist ticker.
    - "watch" / "add" -> add a ticker parsed from the message, else a fixed
      default.
    - anything else -> a short canned reply, no actions.
    This must actually execute a real trade end-to-end when mocked (it's
    what makes the Playwright "AI chat executes a trade" E2E scenario
    possible), so it always resolves to *some* concrete ticker rather than
    ever declining to act.
    """
    lowered = message.lower()
    parsed_ticker = _find_ticker_in_message(message)

    if "buy" in lowered:
        target = parsed_ticker or (watchlist.items[0].ticker if watchlist.items else "AAPL")
        return LLMStructuredResponse(
            message=f"Mock assistant: buying 1 share of {target}.",
            trades=[LLMTradeInstruction(ticker=target, side="buy", quantity=1)],
        )

    if "watch" in lowered or "add" in lowered:
        target = parsed_ticker or DEFAULT_MOCK_WATCH_TICKER
        return LLMStructuredResponse(
            message=f"Mock assistant: adding {target} to your watchlist.",
            watchlist_changes=[LLMWatchlistInstruction(ticker=target, action="add")],
        )

    return LLMStructuredResponse(
        message=(
            "Mock assistant: I can analyze your portfolio, or you can ask me to "
            '"buy <TICKER>" or "watch <TICKER>" to see an action executed.'
        )
    )


# --- Real LLM (LiteLLM -> OpenRouter) ---


def _build_system_prompt(portfolio: PortfolioResponse, watchlist: WatchlistResponse) -> str:
    positions_lines = (
        "\n".join(
            f"  - {p.ticker}: {p.quantity} shares @ avg cost {p.avg_cost:.2f}, "
            f"current price {p.current_price:.2f}, unrealized P&L {p.unrealized_pnl:.2f} "
            f"({p.unrealized_pnl_pct:.2f}%)"
            for p in portfolio.positions
        )
        or "  (no open positions)"
    )
    watchlist_line = ", ".join(
        f"{item.ticker} ({item.current_price if item.current_price is not None else 'n/a'})"
        for item in watchlist.items
    )

    return f"""You are Financial APP, an AI trading assistant for a simulated portfolio (no real money).

Current portfolio:
  Cash balance: {portfolio.cash_balance:.2f}
  Total value: {portfolio.total_value:.2f}
  Total unrealized P&L: {portfolio.total_unrealized_pnl:.2f}
Positions:
{positions_lines}
Watchlist: {watchlist_line}

Instructions:
- Analyze portfolio composition, risk concentration, and P&L when asked.
- Suggest trades with brief reasoning; execute trades when the user asks for one or agrees to one you proposed.
- Manage the watchlist proactively when relevant.
- Be concise and data-driven.
- A trade can only be placed for a ticker already on the watchlist; add it to the watchlist first if needed.
- Respond ONLY with a JSON object matching this shape:
  {{"message": "...", "trades": [{{"ticker": "AAPL", "side": "buy", "quantity": 10}}], "watchlist_changes": [{{"ticker": "PYPL", "action": "add"}}]}}
  "trades" and "watchlist_changes" are optional and should be omitted or empty when there's nothing to execute.
"""


def _call_real_llm(
    portfolio: PortfolioResponse,
    watchlist: WatchlistResponse,
    history_rows: list[sqlite3.Row],
    user_message: str,
) -> LLMStructuredResponse:
    # Imported lazily so LLM_MOCK=true test runs never need litellm to
    # successfully import/configure at module load time.
    from litellm import completion

    system_prompt = _build_system_prompt(portfolio, watchlist)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend({"role": row["role"], "content": row["content"]} for row in history_rows)
    messages.append({"role": "user", "content": user_message})

    try:
        response = completion(model=MODEL, messages=messages, response_format=LLMStructuredResponse)
        raw = response.choices[0].message.content
        return LLMStructuredResponse.model_validate_json(raw)
    except Exception:
        logger.exception("LLM call failed")
        return LLMStructuredResponse(
            message="Sorry, I couldn't reach the AI service just now. Please try again shortly."
        )


# --- Orchestration ---


def process_chat_message(
    conn: sqlite3.Connection,
    provider: MarketDataProvider,
    user_message: str,
    user_id: str = DEFAULT_USER_ID,
) -> ChatResponse:
    conn.execute(
        "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
        "VALUES (?, ?, 'user', ?, NULL, ?)",
        (str(uuid4()), user_id, user_message, _now_iso()),
    )
    conn.commit()

    history_rows = conn.execute(
        "SELECT role, content FROM chat_messages WHERE user_id = ? "
        "ORDER BY created_at ASC LIMIT ?",
        (user_id, CHAT_HISTORY_CONTEXT_LIMIT),
    ).fetchall()

    portfolio_before = get_portfolio(conn, provider, user_id)
    watchlist_before = list_watchlist(conn, provider, user_id)

    if _is_mock_mode():
        structured = _mock_llm_response(user_message, watchlist_before)
    else:
        structured = _call_real_llm(portfolio_before, watchlist_before, history_rows, user_message)

    actions = ChatActions()

    for instruction in structured.trades:
        try:
            execute_trade(conn, provider, instruction.ticker, instruction.quantity, instruction.side, user_id)
            actions.trades.append(
                TradeAction(
                    ticker=instruction.ticker.upper(),
                    side=instruction.side,
                    quantity=instruction.quantity,
                    status="executed",
                )
            )
        except DomainError as exc:
            actions.trades.append(
                TradeAction(
                    ticker=instruction.ticker.upper(),
                    side=instruction.side,
                    quantity=instruction.quantity,
                    status="failed",
                    error=str(exc),
                )
            )

    for instruction in structured.watchlist_changes:
        try:
            if instruction.action == "add":
                add_ticker(conn, provider, instruction.ticker, user_id)
            else:
                remove_ticker(conn, provider, instruction.ticker, user_id)
            actions.watchlist_changes.append(
                WatchlistChangeAction(
                    ticker=instruction.ticker.upper(),
                    action=instruction.action,
                    status="executed",
                )
            )
        except DomainError as exc:
            actions.watchlist_changes.append(
                WatchlistChangeAction(
                    ticker=instruction.ticker.upper(),
                    action=instruction.action,
                    status="failed",
                    error=str(exc),
                )
            )

    # planning/REVIEW.md item 23: actions stores exactly {trades,
    # watchlist_changes} from the LLM response outcome, or null if neither
    # was attempted.
    actions_payload = actions if (actions.trades or actions.watchlist_changes) else None

    assistant_id = str(uuid4())
    assistant_created_at = _now_iso()
    conn.execute(
        "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
        "VALUES (?, ?, 'assistant', ?, ?, ?)",
        (
            assistant_id,
            user_id,
            structured.message,
            actions_payload.model_dump_json() if actions_payload is not None else None,
            assistant_created_at,
        ),
    )
    conn.commit()

    portfolio_after = get_portfolio(conn, provider, user_id)
    assistant_message = ChatMessageResponse(
        id=assistant_id,
        role="assistant",
        content=structured.message,
        actions=actions_payload,
        created_at=assistant_created_at,
    )
    return ChatResponse(message=assistant_message, portfolio=portfolio_after)


# --- Routes ---


@router.get("/chat", response_model=ChatHistoryResponse)
def get_chat_route(conn: sqlite3.Connection = Depends(get_db)) -> ChatHistoryResponse:
    return get_chat_history(conn)


@router.post("/chat", response_model=ChatResponse)
def post_chat_route(
    chat_request: ChatRequest,
    conn: sqlite3.Connection = Depends(get_db),
    provider: MarketDataProvider = Depends(get_provider),
) -> ChatResponse:
    return process_chat_message(conn, provider, chat_request.message)

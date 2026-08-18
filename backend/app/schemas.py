"""Pydantic models — the API contract. See docs/ARCHITECTURE.md.

Every shape here has a matching TypeScript type in frontend/types/api.ts,
field-for-field, same names. If you change one, change the other.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# --- Market data ---


class PriceUpdateEvent(BaseModel):
    """SSE event payload pushed on GET /api/stream/prices."""

    ticker: str
    price: float
    previous_price: float
    timestamp: str
    change_direction: Literal["up", "down", "flat"]


class PricePointResponse(BaseModel):
    price: float
    timestamp: str


class PriceHistoryResponse(BaseModel):
    ticker: str
    points: list[PricePointResponse]


# --- Portfolio ---


class PositionResponse(BaseModel):
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


class PortfolioResponse(BaseModel):
    cash_balance: float
    positions: list[PositionResponse]
    total_value: float
    total_unrealized_pnl: float


class TradeRequest(BaseModel):
    ticker: str
    quantity: float = Field(gt=0)
    side: Literal["buy", "sell"]


class TradeRecord(BaseModel):
    id: str
    ticker: str
    side: Literal["buy", "sell"]
    quantity: float
    price: float
    executed_at: str


class TradeResponse(BaseModel):
    trade: TradeRecord
    portfolio: PortfolioResponse


class PortfolioSnapshotResponse(BaseModel):
    total_value: float
    recorded_at: str


class PortfolioHistoryResponse(BaseModel):
    snapshots: list[PortfolioSnapshotResponse]


# --- Watchlist ---


class WatchlistItemResponse(BaseModel):
    ticker: str
    added_at: str
    current_price: float | None
    previous_price: float | None


class WatchlistResponse(BaseModel):
    items: list[WatchlistItemResponse]


class AddTickerRequest(BaseModel):
    ticker: str = Field(pattern=r"^[A-Z]{1,5}$")


# --- Chat ---


class TradeAction(BaseModel):
    ticker: str
    side: Literal["buy", "sell"]
    quantity: float
    status: Literal["executed", "failed"]
    error: str | None = None


class WatchlistChangeAction(BaseModel):
    ticker: str
    action: Literal["add", "remove"]
    status: Literal["executed", "failed"]
    error: str | None = None


class ChatActions(BaseModel):
    trades: list[TradeAction] = Field(default_factory=list)
    watchlist_changes: list[WatchlistChangeAction] = Field(default_factory=list)


class ChatMessageResponse(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    actions: ChatActions | None
    created_at: str


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageResponse]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    message: ChatMessageResponse
    portfolio: PortfolioResponse


# --- LLM structured output ---
# What the model itself returns, before execution status is known.
# Distinct from ChatActions, which records the outcome after trades/watchlist
# changes have been attempted.


class LLMTradeInstruction(BaseModel):
    ticker: str
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)


class LLMWatchlistInstruction(BaseModel):
    ticker: str
    action: Literal["add", "remove"]


class LLMStructuredResponse(BaseModel):
    message: str
    trades: list[LLMTradeInstruction] = Field(default_factory=list)
    watchlist_changes: list[LLMWatchlistInstruction] = Field(default_factory=list)


# --- System ---


class HealthResponse(BaseModel):
    status: Literal["ok"]

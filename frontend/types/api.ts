// TypeScript types mirroring backend/app/schemas.py, field-for-field.
// If you change one, change the other. See docs/ARCHITECTURE.md.

export type ChangeDirection = "up" | "down" | "flat";

export interface PriceUpdateEvent {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: string;
  change_direction: ChangeDirection;
}

export interface PricePoint {
  price: number;
  timestamp: string;
}

export interface PriceHistoryResponse {
  ticker: string;
  points: PricePoint[];
}

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
}

export interface Portfolio {
  cash_balance: number;
  positions: Position[];
  total_value: number;
  total_unrealized_pnl: number;
}

export type TradeSide = "buy" | "sell";

export interface TradeRequest {
  ticker: string;
  quantity: number;
  side: TradeSide;
}

export interface TradeRecord {
  id: string;
  ticker: string;
  side: TradeSide;
  quantity: number;
  price: number;
  executed_at: string;
}

export interface TradeResponse {
  trade: TradeRecord;
  portfolio: Portfolio;
}

export interface PortfolioSnapshot {
  total_value: number;
  recorded_at: string;
}

export interface PortfolioHistoryResponse {
  snapshots: PortfolioSnapshot[];
}

export interface WatchlistItem {
  ticker: string;
  added_at: string;
  current_price: number | null;
  previous_price: number | null;
}

export interface WatchlistResponse {
  items: WatchlistItem[];
}

export interface AddTickerRequest {
  ticker: string;
}

export type ActionStatus = "executed" | "failed";

export interface TradeAction {
  ticker: string;
  side: TradeSide;
  quantity: number;
  status: ActionStatus;
  error: string | null;
}

export type WatchlistAction = "add" | "remove";

export interface WatchlistChangeAction {
  ticker: string;
  action: WatchlistAction;
  status: ActionStatus;
  error: string | null;
}

export interface ChatActions {
  trades: TradeAction[];
  watchlist_changes: WatchlistChangeAction[];
}

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  actions: ChatActions | null;
  created_at: string;
}

export interface ChatHistoryResponse {
  messages: ChatMessage[];
}

export interface ChatRequest {
  message: string;
}

export interface ChatResponse {
  message: ChatMessage;
  portfolio: Portfolio;
}

export interface HealthResponse {
  status: "ok";
}

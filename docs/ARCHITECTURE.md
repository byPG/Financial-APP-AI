# Finance App — Architecture & Contract

This is the technical contract for the build. Every agent reads this before starting work. It makes concrete everything `planning/PLAN.md` left as a decision (library versions, schemas, the market data interface) — where this document and `PLAN.md` conflict, this document wins for implementation detail, but neither changes the product decisions already resolved in `planning/REVIEW.md`.

Source-of-truth files (not just described here — they exist in the repo and must stay in sync):

- `backend/app/schemas.py` — Pydantic models for every request/response
- `backend/app/market_data/base.py` — the abstract market data interface
- `frontend/types/api.ts` — TypeScript types mirroring `schemas.py`, field-for-field

If you change a shape, change it in the code file, then update the other side (Pydantic ↔ TS) and this document in the same change.

---

## 1. Tech Stack (concrete versions)

### Backend

| Library | Version | Purpose |
| --- | --- | --- |
| Python | 3.12 | language |
| FastAPI | >=0.115 | web framework |
| uvicorn[standard] | >=0.32 | ASGI server |
| pydantic | >=2.9 | schemas/validation |
| sse-starlette | >=2.1 | `EventSourceResponse` for `/api/stream/prices` |
| litellm | >=1.50 | LLM calls via OpenRouter (see the `openrouter-free` skill) |
| httpx | >=0.27 | Massive API client, test client |
| python-dotenv | >=1.0 | loads `.env` |
| pytest / pytest-asyncio | >=8.3 / >=0.24 | unit tests |
| ruff | >=0.7 | lint/format |

Dependency management: `uv`, declared in `backend/pyproject.toml`. `package = false` — this is an application, not a distributable library, so there's no `src/` build-backend layout, just `backend/app/`.

Database access: stdlib `sqlite3`, raw parameterized SQL (see `planning/PLAN.md` Section 7). No ORM — the schema is simple enough that an ORM would be net-negative complexity. WAL mode enabled on connect (Section 7, Concurrency & Safety).

### Frontend

| Library | Version | Purpose |
| --- | --- | --- |
| Next.js | ^15.1 | framework, static export (`output: "export"`) |
| React / react-dom | ^19.0 | UI |
| TypeScript | ^5.6 | types |
| Tailwind CSS | ^4.0 | styling (CSS-first config via `@theme` in `globals.css`, no `tailwind.config.ts` needed in v4) |
| lightweight-charts | ^4.2 | main ticker chart + watchlist sparklines — canvas-based, built for exactly this (frequent updates, financial time series) |
| recharts | ^2.13 | portfolio heatmap (`Treemap`) + P&L line chart — these update infrequently (on trade / ~30s snapshot), so SVG rendering is not a performance concern, and Recharts' `Treemap` is the only piece lightweight-charts can't do |
| vitest + @testing-library/react | ^2.1 / ^16.0 | unit tests |

Package manager: npm (matches the Dockerfile's `npm install && npm run build`).

**Two charting libraries, deliberately**: PLAN.md Section 10 says "canvas-based charting library preferred (Lightweight Charts or Recharts)" but Recharts is SVG-based, not canvas — that line in PLAN.md is imprecise. Lightweight-charts is the canvas one and is used wherever update frequency matters (main chart, sparklines, both driven by the ~500ms SSE stream). Recharts is used only for the treemap (no lightweight-charts equivalent) and the P&L chart (low update frequency, SVG is fine).

### Infra

Everything in `planning/PLAN.md` Sections 5, 11, 16 stands as written (env vars, Docker bind mount, non-goals). Not repeated here.

---

## 2. Directory Boundaries (concrete)

```
backend/
├── pyproject.toml          # Architect — dependencies declared
├── .python-version         # Architect — "3.12"
├── app/
│   ├── __init__.py
│   ├── schemas.py           # Architect — Pydantic models (contract)
│   ├── market_data/
│   │   ├── __init__.py
│   │   └── base.py          # Architect — abstract interface (contract)
│   │   └── simulator.py     # Market Data Engineer
│   │   └── massive_client.py # Market Data Engineer
│   ├── main.py               # Backend Engineer — FastAPI app, routes
│   ├── db/                   # Backend Engineer — schema.sql, seed, connection helpers
│   ├── portfolio.py          # Backend Engineer — trade execution, P&L
│   ├── chat.py                # Backend Engineer — LLM integration
│   └── ...                    # further internal structure is the Backend Engineer's call
└── tests/                     # Market Data Engineer + Backend Engineer, per PLAN.md Section 12

frontend/
├── package.json              # Architect — dependencies declared
├── tsconfig.json             # Architect
├── next.config.ts            # Architect — output: "export"
├── types/
│   └── api.ts                 # Architect — TS types (contract)
└── app/, components/, ...     # Frontend Engineer — everything else
```

The Market Data Engineer implements `simulator.py` and `massive_client.py` against `market_data/base.py`. The Backend Engineer implements everything else in `app/` and consumes `market_data/base.py` — neither writes the other's files.

---

## 3. Market Data Provider Interface

Defined in `backend/app/market_data/base.py`. Both the simulator and the Massive client subclass `MarketDataProvider`. Backend code (SSE streaming, trade execution) depends only on this interface, never on a concrete implementation.

```python
class MarketDataProvider(ABC):
    async def start(self) -> None: ...      # begin the background update loop
    async def stop(self) -> None: ...
    def watch(self, ticker: str) -> None: ...    # start tracking (watchlist add)
    def unwatch(self, ticker: str) -> None: ...  # stop tracking (watchlist remove)
    def get_latest(self, ticker: str) -> PriceSnapshot | None: ...
    def get_history(self, ticker: str) -> list[PricePoint]: ...  # ~30min downsampled, ~10-15s spacing
```

`watch`/`unwatch` are called by the watchlist endpoints (Section 8 of `PLAN.md`) so the cache and the ticker scope (`planning/PLAN.md` Section 14) stay in sync automatically — the API layer never touches the price cache directly.

---

## 4. API Contract

Full request/response bodies live in `backend/app/schemas.py` (Pydantic) and `frontend/types/api.ts` (TypeScript) — identical shapes, snake_case field names on both sides (no case translation layer). Status codes and error semantics not visible in the schemas:

| Method | Path | Request | Response | Notes |
| --- | --- | --- | --- | --- |
| GET | `/api/stream/prices` | — | SSE stream of `PriceUpdateEvent` | `text/event-stream`, one event per ticker per tick |
| GET | `/api/prices/{ticker}/history` | — | `PriceHistoryResponse` | 404 if ticker not tracked |
| GET | `/api/portfolio` | — | `PortfolioResponse` | |
| POST | `/api/portfolio/trade` | `TradeRequest` | `TradeResponse` | 400: insufficient cash/shares, ticker not on watchlist, bad ticker format |
| GET | `/api/portfolio/history` | — | `PortfolioHistoryResponse` | |
| GET | `/api/watchlist` | — | `WatchlistResponse` | |
| POST | `/api/watchlist` | `AddTickerRequest` | `WatchlistItemResponse` | 200 idempotent if already present; 400 if ticker fails `^[A-Z]{1,5}$` |
| DELETE | `/api/watchlist/{ticker}` | — | 204 No Content | 404 if not found; 409 if an open position exists |
| GET | `/api/chat` | — | `ChatHistoryResponse` | most recent N messages, oldest first |
| POST | `/api/chat` | `ChatRequest` | `ChatResponse` | single JSON response, no streaming transport (`PLAN.md` Section 9) |
| GET | `/api/health` | — | `HealthResponse` | |

All 4xx errors use FastAPI's default `{"detail": "..."}` shape — no custom error envelope.

### `actions` field note

`ChatMessageResponse.actions` is `{trades, watchlist_changes}`, matching the LLM's structured output (`PLAN.md` Section 9), but each entry is augmented with `status: "executed" | "failed"` and an optional `error` — the frontend needs this to render trade/watchlist confirmations inline (`PLAN.md` Section 10). This is the one place the stored shape isn't a byte-for-byte copy of the LLM's raw output; the LLM's raw `LLMStructuredResponse` (see `schemas.py`) is the internal type used only between the LLM call and the execution step.

---

## 5. SSE Event Schema

`GET /api/stream/prices` — each `data:` line is one `PriceUpdateEvent` JSON object:

```json
{"ticker": "AAPL", "price": 191.32, "previous_price": 190.87, "timestamp": "2026-08-19T10:15:03.512Z", "change_direction": "up"}
```

One event per ticker per tick (not a batched array) — simpler on both ends, and `EventSourceResponse` (sse-starlette) handles the framing.

---

## 6. What's Scaffolded vs. What's Not

Created by this pass (Architect, Phase 1):

- `docs/ARCHITECTURE.md` (this file)
- `backend/pyproject.toml`, `backend/.python-version`
- `backend/app/__init__.py`, `backend/app/schemas.py`
- `backend/app/market_data/__init__.py`, `backend/app/market_data/base.py`
- `frontend/package.json`, `frontend/tsconfig.json`, `frontend/next.config.ts`
- `frontend/types/api.ts`
- `.gitignore` updated with Node/Next.js patterns

Not created — explicitly the next phases' work:

- No `uv.lock` / `package-lock.json` yet — the Market Data Engineer / Backend Engineer / Frontend Engineer generate these on first `uv sync` / `npm install`
- No application code: no `main.py`, no simulator/Massive implementations, no React components, no `Dockerfile`, no `scripts/`, no `test/` (Playwright)
- `db/` schema SQL and seed logic — Backend Engineer, per `PLAN.md` Section 4

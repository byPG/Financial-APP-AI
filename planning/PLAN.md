# Finance App — AI Trading Workstation

## Project Specification

## 1. Vision

Finance App is a visually stunning AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot.

This is the capstone project for an agentic AI coding course. It is built entirely by Coding Agents demonstrating how orchestrated AI agents can produce a production-quality full-stack application. Agents interact through files in `planning/` (product spec and process docs, including this file) and `docs/` (the technical contract — `ARCHITECTURE.md` — produced by the Architect agent; see Section 4).

## 2. User Experience

### First Launch

The user runs a single Docker command (or a provided start script). A browser opens to `http://localhost:8000`. No login, no signup. They immediately see:

- A watchlist of 10 default tickers with live-updating prices in a grid
- $10,000 in virtual cash
- A dark, data-rich trading terminal aesthetic
- An AI chat panel ready to assist

### What the User Can Do

- **Watch prices stream** — prices flash green (uptick) or red (downtick) with subtle CSS animations that fade
- **View sparkline mini-charts** — last 30 minutes of price action beside each ticker in the watchlist
- **Click a ticker** to see a larger detailed chart in the main chart area
- **Buy and sell shares** — market orders only, instant fill at current price, no fees, no confirmation dialog
- **Monitor their portfolio** — a heatmap (treemap) showing positions sized by weight and colored by P&L, plus a P&L chart tracking total portfolio value over time
- **View a positions table** — ticker, quantity, average cost, current price, unrealized P&L, % change
- **Chat with the AI assistant** — ask about their portfolio, get analysis, and have the AI execute trades and manage the watchlist through natural language
- **Manage the watchlist** — add/remove tickers manually or via the AI chat

### Visual Design

- **Dark theme**: backgrounds around `#0d1117` or `#1a1a2e`, muted gray borders, no pure black
- **Price flash animations**: brief green/red background highlight on price change, fading over ~500ms via CSS transitions
- **Connection status indicator**: a small colored dot (green = connected, yellow = reconnecting, red = disconnected) visible in the header
- **Professional, data-dense layout**: inspired by Bloomberg/trading terminals — every pixel earns its place
- **Responsive but desktop-first**: optimized for wide screens, functional on tablet

Brand colors:

## Color Scheme

- Accent Yellow: `#ecad0a`
- Blue Primary: `#209dd7`
- Purple Secondary: `#753991` (submit buttons)

## 3. Architecture Overview

### Single Container, Single Port

```
┌─────────────────────────────────────────────────┐
│  Docker Container (port 8000)                   │
│                                                 │
│  FastAPI (Python/uv)                            │
│  ├── /api/*          REST endpoints             │
│  ├── /api/stream/*   SSE streaming              │
│  └── /*              Static file serving         │
│                      (Next.js export)            │
│                                                 │
│  SQLite database (volume-mounted)               │
│  Background task: market data polling/sim        │
└─────────────────────────────────────────────────┘
```

- **Frontend**: Next.js with TypeScript, built as a static export (`output: 'export'`), served by FastAPI as static files
- **Backend**: FastAPI (Python), managed as a `uv` project
- **Database**: SQLite, single file at `db/finally.db`, volume-mounted for persistence
- **Real-time data**: Server-Sent Events (SSE) — simpler than WebSockets, one-way server→client push, works everywhere
- **AI integration**: LiteLLM → OpenRouter (free-tier model, no inference cost), with structured outputs for trade execution
- **Market data**: Environment-variable driven — simulator by default, real data via Massive API if key provided

### Why These Choices

| Decision                | Rationale                                                                                     |
| ----------------------- | --------------------------------------------------------------------------------------------- |
| SSE over WebSockets     | One-way push is all we need; simpler, no bidirectional complexity, universal browser support  |
| Static Next.js export   | Single origin, no CORS issues, one port, one container, simple deployment                     |
| SQLite over Postgres    | No auth = no multi-user = no need for a database server; self-contained, zero config          |
| Single Docker container | Students run one command; no docker-compose for production, no service orchestration          |
| uv for Python           | Fast, modern Python project management; reproducible lockfile; what students should learn     |
| Market orders only      | Eliminates order book, limit order logic, partial fills — dramatically simpler portfolio math |

---

## 4. Directory Structure

```
finally/
├── frontend/                 # Next.js TypeScript project (static export)
├── backend/                  # FastAPI uv project (Python)
│   └── db/                   # Schema definitions, seed data, migration logic
├── docs/                     # Technical contract for agents
│   └── ARCHITECTURE.md       # Produced by the Architect agent; all other agents read this first
├── planning/                 # Project-wide product/process documentation for agents
│   ├── PLAN.md               # This document
│   └── ...                   # Additional agent reference docs
├── scripts/
│   ├── start_mac.sh          # Launch Docker container (macOS/Linux)
│   ├── stop_mac.sh           # Stop Docker container (macOS/Linux)
│   ├── start_windows.ps1     # Launch Docker container (Windows PowerShell)
│   └── stop_windows.ps1      # Stop Docker container (Windows PowerShell)
├── test/                     # Playwright E2E tests + docker-compose.test.yml
├── db/                       # Volume mount target (SQLite file lives here at runtime)
│   └── .gitkeep              # Directory exists in repo; finally.db is gitignored
├── Dockerfile                # Multi-stage build (Node → Python)
├── docker-compose.yml        # Optional convenience wrapper
├── .env                      # Environment variables (gitignored, .env.example committed)
└── .gitignore
```

### Key Boundaries

- **`frontend/`** is a self-contained Next.js project. It knows nothing about Python. It talks to the backend via `/api/*` endpoints and `/api/stream/*` SSE endpoints. Internal structure is up to the Frontend Engineer agent.
- **`backend/`** is a self-contained uv project with its own `pyproject.toml`. It owns all server logic including database initialization, schema, seed data, API routes, SSE streaming, market data, and LLM integration. Internal structure is up to the Backend/Market Data agents.
- **`backend/db/`** contains schema SQL definitions and seed logic. The backend lazily initializes the database on first request — creating tables and seeding default data if the SQLite file doesn't exist or is empty.
- **`db/`** at the top level is the runtime volume mount point. The SQLite file (`db/finally.db`) is created here by the backend and persists across container restarts via Docker volume.
- **`docs/`** contains project-wide documentation. The Architect agent produces `ARCHITECTURE.md` here, which all other agents reference as the contract.
- **`test/`** contains Playwright E2E tests and supporting infrastructure (e.g., `docker-compose.test.yml`). Unit tests live within `frontend/` and `backend/` respectively, following each framework's conventions.
- **`scripts/`** contains start/stop scripts that wrap Docker commands.

---

## 5. Environment Variables

```bash
# Required: OpenRouter API key for LLM chat functionality
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Optional: Massive (Polygon.io) API key for real market data
# If not set, the built-in market simulator is used (recommended for most users)
MASSIVE_API_KEY=

# Optional: Set to "true" for deterministic mock LLM responses (testing)
LLM_MOCK=false
```

### Behavior

- If `MASSIVE_API_KEY` is set and non-empty → backend uses Massive REST API for market data
- If `MASSIVE_API_KEY` is absent or empty → backend uses the built-in market simulator
- If `LLM_MOCK=true` → backend returns deterministic mock LLM responses (for E2E tests)
- The backend reads `.env` from the project root (mounted into the container or read via docker `--env-file`)

---

## 6. Market Data

### Two Implementations, One Interface

Both the simulator and the Massive client implement the same abstract interface. The backend selects which to use based on the environment variable. All downstream code (SSE streaming, price cache, frontend) is agnostic to the source.

### Simulator (Default)

- Generates prices using geometric Brownian motion (GBM) with configurable drift and volatility per ticker
- Updates at ~500ms intervals
- Correlated moves across tickers (e.g., tech stocks move together)
- Occasional random "events" — sudden 2-5% moves on a ticker for drama
- Starts from realistic seed prices (e.g., AAPL ~$190, GOOGL ~$175, etc.)
- Runs as an in-process background task — no external dependencies

### Massive API (Optional)

- REST API polling (not WebSocket) — simpler, works on all tiers
- Polls for the union of all watched tickers on a configurable interval
- Free tier (5 calls/min): poll every 15 seconds — confirm against Massive/Polygon.io's current free-tier rate limits at implementation time, as third-party limits change
- Paid tiers: poll every 2-15 seconds depending on tier
- Parses REST response into the same format as the simulator

### Shared Price Cache

- A single background task (simulator or Massive poller) writes to an in-memory price cache
- The cache holds the latest price, previous price, and timestamp for each ticker
- The cache only tracks tickers currently on the watchlist (see Section 14, Ticker Scope)
- SSE streams read from this cache and push updates to connected clients
- This architecture supports future multi-user scenarios without changes to the data layer

### Price History (for sparklines and the main chart)

- The same background task also appends a downsampled point per ticker to an in-memory ring buffer, roughly every 10-15 seconds (not every ~500ms tick) — a 30-minute window is then ~120-180 points per ticker, cheap to hold and serialize
- No database table is needed — this history resets on restart, which is acceptable since it's presentation-only data
- Exposed via `GET /api/prices/{ticker}/history` (see Section 8) for both the watchlist sparklines and the main chart

### SSE Streaming

- Endpoint: `GET /api/stream/prices`
- Long-lived SSE connection; client uses native `EventSource` API
- Server pushes price updates for all watched tickers at a regular cadence (~500ms)
- Each SSE event contains ticker, price, previous price, timestamp, and change direction
- Client handles reconnection automatically (EventSource has built-in retry)

---

## 7. Database

### SQLite with Lazy Initialization

The backend checks for the SQLite database on startup (or first request). If the file doesn't exist or tables are missing, it creates the schema and seeds default data. This means:

- No separate migration step
- No manual database setup
- Fresh Docker volumes start with a clean, seeded database automatically

### Concurrency & Safety

- At least three writers hit the same SQLite file (trade execution, the periodic portfolio-snapshot task, chat message persistence). Enable WAL mode (`PRAGMA journal_mode=WAL`) on connection and keep transactions short, so concurrent writes don't raise "database is locked" errors.
- All queries are parameterized (no string-built SQL), including for ticker/quantity/side values that originate from LLM-generated trades — that data is untrusted input from the backend's perspective regardless of source.

### Schema

All tables include a `user_id` column defaulting to `"default"`. This is hardcoded for now (single-user) but enables future multi-user support without schema migration.

**users_profile** — User state (cash balance)

- `id` TEXT PRIMARY KEY (default: `"default"`)
- `cash_balance` REAL (default: `10000.0`)
- `created_at` TEXT (ISO timestamp)

**watchlist** — Tickers the user is watching

- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `added_at` TEXT (ISO timestamp)
- UNIQUE constraint on `(user_id, ticker)`

**positions** — Current holdings

- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `quantity` REAL
- `avg_cost` REAL
- `updated_at` TEXT (ISO timestamp)

**trades** — Trade history (append-only log)

- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `side` TEXT (`"buy"` or `"sell"`)
- `quantity` REAL
- `price` REAL
- `executed_at` TEXT (ISO timestamp)

**portfolio_snapshots** — Portfolio value over time (for P&L chart)

- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `total_value` REAL
- `recorded_at` TEXT (ISO timestamp)

**chat_messages** — Conversation history with LLM

- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `role` TEXT (`"user"` or `"assistant"`)
- `content` TEXT
- `actions` TEXT (JSON — trades executed, watchlist changes made; null for user messages)
- `created_at` TEXT (ISO timestamp)

### Default Seed Data

- One user profile: `id="default"`, `cash_balance=10000.0`
- Ten watchlist entries: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX

---

## 8. API Endpoints

### Market Data

| Method | Path                            | Description                                                            |
| ------ | -------------------------------- | ----------------------------------------------------------------------- |
| GET    | `/api/stream/prices`             | SSE stream of live price updates                                        |
| GET    | `/api/prices/{ticker}/history`   | Downsampled price history for the last 30 min (sparklines, main chart)  |

### Portfolio

| Method | Path                     | Description                                                  |
| ------ | ------------------------ | ------------------------------------------------------------ |
| GET    | `/api/portfolio`         | Current positions, cash balance, total value, unrealized P&L |
| POST   | `/api/portfolio/trade`   | Execute a trade: `{ticker, quantity, side}`. `ticker` must be on the watchlist (Section 14, Ticker Scope), else 400 |
| GET    | `/api/portfolio/history` | Portfolio value snapshots over time (for P&L chart)          |

### Watchlist

| Method | Path                      | Description                                  |
| ------ | ------------------------- | -------------------------------------------- |
| GET    | `/api/watchlist`          | Current watchlist tickers with latest prices |
| POST   | `/api/watchlist`          | Add a ticker: `{ticker}`. Must match `^[A-Z]{1,5}$`, else 400. Re-adding an existing ticker is idempotent (200, no error) |
| DELETE | `/api/watchlist/{ticker}` | Remove a ticker. 404 if not found, 409 if an open position exists for it (Section 14, Ticker Scope) |

### Chat

| Method | Path        | Description                                                                |
| ------ | ----------- | ---------------------------------------------------------------------------- |
| GET    | `/api/chat` | Recent conversation history, to repopulate the chat panel on page load       |
| POST   | `/api/chat` | Send a message, receive the complete LLM response as one JSON payload (Section 9) |

### System

| Method | Path          | Description                          |
| ------ | ------------- | ------------------------------------ |
| GET    | `/api/health` | Health check (for Docker/deployment) |

---

## 9. LLM Integration

When writing code to make calls to LLMs, use the openrouter-free skill to use LiteLLM via OpenRouter to a free-tier OpenRouter model (no inference cost) — currently `openrouter/google/gemma-4-26b-a4b-it:free`; OpenRouter's free-tier catalog changes over time, so confirm the model is still free and supports structured outputs before relying on it. Structured Outputs should be used to interpret the results.

There is an OPENROUTER_API_KEY in the .env file in the project root.

### How It Works

When the user sends a chat message, the backend:

1. Loads the user's current portfolio context (cash, positions with P&L, watchlist with live prices, total portfolio value)
2. Loads recent conversation history from the `chat_messages` table
3. Constructs a prompt with a system message, portfolio context, conversation history, and the user's new message
4. Calls the LLM via LiteLLM → OpenRouter, requesting structured output, using the openrouter-free skill
5. Parses the structured response
6. Auto-executes any trades or watchlist changes specified in the response
7. Stores the message and executed actions in `chat_messages` (`actions` is exactly `{trades, watchlist_changes}` as returned by the LLM, or `null` if both are empty)
8. Returns the complete `message` text in a single JSON response — see Transport & Streaming below

### Structured Output Schema

The LLM is instructed to respond with JSON matching this schema:

```json
{
  "message": "Your conversational response to the user",
  "trades": [{ "ticker": "AAPL", "side": "buy", "quantity": 10 }],
  "watchlist_changes": [{ "ticker": "PYPL", "action": "add" }]
}
```

- `message` (required): The conversational text shown to the user
- `trades` (optional): Array of trades to auto-execute. Each trade goes through the same validation as manual trades (sufficient cash for buys, sufficient shares for sells, ticker on the watchlist) — the LLM's output is untrusted input from the backend's perspective and is validated server-side like any other request
- `watchlist_changes` (optional): Array of watchlist modifications

### Transport & Streaming

`POST /api/chat` is a single request/response — no SSE, no chunked transfer. The backend waits for the complete structured response from the LLM, executes any trades/watchlist changes, persists the message, and returns the finished `message` text as one JSON payload. The frontend applies a client-side typewriter animation to that text for the "streaming" feel described in Sections 2 and 10. This is deliberately simpler than incremental JSON parsing, which the structured-output schema doesn't support cleanly anyway (a client can't safely act on partial JSON).

### Auto-Execution

Trades specified by the LLM execute automatically — no confirmation dialog. This is a deliberate design choice:

- It's a simulated environment with fake money, so the stakes are zero
- It creates an impressive, fluid demo experience
- It demonstrates agentic AI capabilities — the core theme of the course

If a trade fails validation (e.g., insufficient cash), the error is included in the chat response so the LLM can inform the user.

### System Prompt Guidance

The LLM should be prompted as "Financial APP, an AI trading assistant" with instructions to:

- Analyze portfolio composition, risk concentration, and P&L
- Suggest trades with reasoning
- Execute trades when the user asks or agrees
- Manage the watchlist proactively
- Be concise and data-driven in responses
- Always respond with valid structured JSON

### LLM Mock Mode

When `LLM_MOCK=true`, the backend returns deterministic mock responses instead of calling OpenRouter. This enables:

- Fast, free, reproducible E2E tests
- Development without an API key
- CI/CD pipelines

Mock responses are selected with simple keyword matching on the user's message (e.g., a message containing "buy" returns a canned response with a `trades` entry; a message containing "watch" or "add" returns one with a `watchlist_changes` entry; anything else returns a generic canned reply). This is enough to let the Playwright "AI chat executes a trade" scenario (Section 12) actually trigger a trade deterministically, without needing a real keyword parser.

---

## 10. Frontend Design

### Layout

The frontend is a single-page application with a dense, terminal-inspired layout. The specific component architecture and layout system is up to the Frontend Engineer, but the UI should include these elements:

- **Watchlist panel** — grid/table of watched tickers with: ticker symbol, current price (flashing green/red on change), daily change %, and a sparkline mini-chart (last 30 min)
- **Main chart area** — larger chart for the currently selected ticker, with at minimum price over time. Clicking a ticker in the watchlist selects it here. Defaults to the first watchlist ticker on initial load.
- **Portfolio heatmap** — treemap visualization where each rectangle is a position, sized by portfolio weight, colored by P&L (green = profit, red = loss)
- **P&L chart** — line chart showing total portfolio value over time, using data from `portfolio_snapshots`
- **Positions table** — tabular view of all positions: ticker, quantity, avg cost, current price, unrealized P&L, % change
- **Trade bar** — simple input area: ticker field, quantity field, buy button, sell button. Market orders, instant fill.
- **AI chat panel** — docked/collapsible sidebar. Message input, scrolling conversation history, client-side typewriter animation for assistant responses (see Section 9, Transport & Streaming). Trade executions and watchlist changes shown inline as confirmations. Populated from `GET /api/chat` on page load.
- **Header** — portfolio total value (updating live), connection status indicator, cash balance

### Technical Notes

- Use `EventSource` for SSE connection to `/api/stream/prices`
- Canvas-based charting library preferred (Lightweight Charts or Recharts) for performance
- Price flash effect: on receiving a new price, briefly apply a CSS class with background color transition, then remove it
- All API calls go to the same origin (`/api/*`) — no CORS configuration needed
- Tailwind CSS for styling with a custom dark theme

---

## 11. Docker & Deployment

### Multi-Stage Dockerfile

```
Stage 1: Node 20 slim
  - Copy frontend/
  - npm install && npm run build (produces static export)

Stage 2: Python 3.12 slim
  - Install uv
  - Copy backend/
  - uv sync (install Python dependencies from lockfile)
  - Copy frontend build output into a static/ directory
  - Expose port 8000
  - CMD: uvicorn serving FastAPI app
```

FastAPI serves the static frontend files and all API routes on port 8000.

### Docker Volume

The SQLite database persists via a bind mount of the repo's `db/` directory, so students can see the database file directly on disk rather than in an opaque Docker-managed volume:

```bash
docker run -v "$(pwd)/db:/app/db" -p 8000:8000 --env-file .env finally
```

The `db/` directory in the project root maps to `/app/db` in the container. The backend writes `finally.db` to this path. This matches Section 4's directory structure, where `db/` is a repo directory with a gitignored `finally.db`.

### Start/Stop Scripts

**`scripts/start_mac.sh`** (macOS/Linux):

- Builds the Docker image if not already built (or if `--build` flag passed)
- Runs the container with the volume mount, port mapping, and `.env` file
- Prints the URL to access the app
- Optionally opens the browser

**`scripts/stop_mac.sh`** (macOS/Linux):

- Stops and removes the running container
- Does NOT remove the volume (data persists)

**`scripts/start_windows.ps1`** / **`scripts/stop_windows.ps1`**: PowerShell equivalents for Windows, same behavior as the `_mac` scripts above.

All scripts should be idempotent — safe to run multiple times.

---

## 12. Testing Strategy

### Unit Tests (within `frontend/` and `backend/`)

**Backend (pytest)**:

- Market data: simulator generates valid prices, GBM math is correct, Massive API response parsing works, both implementations conform to the abstract interface
- Portfolio: trade execution logic, P&L calculations, edge cases (selling more than owned, buying with insufficient cash, selling at a loss)
- LLM: structured output parsing handles all valid schemas, graceful handling of malformed responses, trade validation within chat flow
- API routes: correct status codes, response shapes, error handling

**Frontend (React Testing Library or similar)**:

- Component rendering with mock data
- Price flash animation triggers correctly on price changes
- Watchlist CRUD operations
- Portfolio display calculations
- Chat message rendering and streaming

### E2E Tests (in `test/`)

**Infrastructure**: A separate `docker-compose.test.yml` in `test/` that spins up the app container plus a Playwright container. This keeps browser dependencies out of the production image.

**Environment**: Tests run with `LLM_MOCK=true` by default for speed and determinism.

**Key Scenarios**:

- Fresh start: default watchlist appears, $10k balance shown, prices are streaming
- Add and remove a ticker from the watchlist
- Buy shares: cash decreases, position appears, portfolio updates
- Sell shares: cash increases, position updates or disappears
- Portfolio visualization: heatmap renders with correct colors, P&L chart has data points
- AI chat (mocked): send a message, receive a response, trade execution appears inline
- SSE resilience: disconnect and verify reconnection

---

## 13. Sub-Agent Architecture

This project is built by Claude Code using a sub-agent orchestration pattern. The Integration Lead (main Claude Code process) delegates to specialized sub-agents, each with focused context and clear boundaries.

### Agent Roles

**Architect** (runs first, all others depend on its output)

- Produces `docs/ARCHITECTURE.md` — the definitive contract for all agents
- Defines the shared API contract (request/response schemas for every endpoint)
- Defines the market data provider abstract interface
- Defines Pydantic models (backend) and TypeScript types (frontend) that must stay in sync
- Makes all technology decisions concrete (specific library versions, configuration patterns)
- Scaffolds the empty-but-configured `backend/pyproject.toml` and `frontend/package.json` project skeletons (dependencies declared, no application code) so the Market Data Engineer and Frontend Engineer have a shared project to build into from Phase 2 onward
- Does NOT write application code — only contracts, types, interfaces, and the project skeletons above

**Market Data Engineer**

- Owns the market data subsystem within the backend
- Implements the simulator (GBM, correlated moves, events)
- Implements the Massive API client
- Implements the abstract interface defined by the Architect
- Writes unit tests for both implementations
- Has no knowledge of or dependency on the frontend

**Backend Engineer**

- Owns the FastAPI application, API routes, SSE streaming, portfolio logic, and LLM integration
- Implements database initialization (schema creation, seeding) in `backend/db/`
- Consumes the market data interface (does not implement it)
- Writes unit tests for all API endpoints and business logic
- Has no knowledge of frontend implementation details

**Frontend Engineer**

- Owns the entire Next.js project
- Builds all UI components, Tailwind styling, SSE client, charts, animations, chat interface
- Works against the API contract from the Architect — does not need to know backend internals
- Writes component tests
- Has no knowledge of Python or backend implementation

**DevOps Engineer**

- Owns the Dockerfile, docker-compose files, start/stop scripts, and `.env.example`
- Builds and validates the multi-stage Docker image
- Sets up the Playwright test infrastructure in `test/`
- Can work in parallel with other agents — only needs the Architect's output
- Has no knowledge of application business logic

**Integration Lead** (the orchestrator — the main Claude Code process)

- Runs agents in the correct order respecting dependencies
- After each agent: runs that agent's tests, verifies the build, checks for contract violations
- Routes failures back to the responsible agent with context
- Runs the full Docker build and Playwright E2E suite as final validation
- Maximum 3 retries per agent per issue before escalating

### Execution Order

```
Phase 1:  Architect → validate ARCHITECTURE.md exists and is complete

Phase 2:  Market Data Engineer → unit tests pass
          DevOps Engineer → Dockerfile authored and syntactically valid, start/stop scripts idempotent
          (these two run in parallel; a full "image builds and runs" check isn't possible yet —
          frontend/ and backend/ application code don't exist until Phases 3-4 — that check moves to Phase 5)

Phase 3:  Backend Engineer → unit tests pass, API serves correctly

Phase 4:  Frontend Engineer → build succeeds, component tests pass

Phase 5:  Integration Lead → full Docker build → Playwright E2E suite
          On failure → identify responsible agent → route fix → retry
```

### Agent Boundaries — Critical Rules

- Every agent reads `docs/ARCHITECTURE.md` before starting work
- No agent modifies files outside its ownership boundary
- The API contract (endpoint paths, request/response shapes) is defined by the Architect and is immutable once set — agents implement to the contract, not around it
- If an agent discovers the contract is insufficient, it reports back to the Integration Lead rather than improvising
- The Market Data Engineer and Backend Engineer share the `backend/` directory but own different subdirectories within it — the Architect must define this boundary clearly

---

## 14. Portfolio Logic

### Trading Rules

- **Market orders only**: trades execute instantly at the current price from the price cache
- **No fees or slippage**: price paid = current cached price
- **Buy validation**: `quantity * price <= cash_balance`
- **Sell validation**: user must own >= `quantity` shares of that ticker
- **Position updates**: buying increases quantity and recalculates average cost; selling decreases quantity. Average-cost accounting only — the schema's single `avg_cost` column doesn't support per-lot (FIFO) tracking
- **Position removal**: when quantity reaches 0 after a sell, the position row is deleted. Realized P&L is out of scope for v1 (it's derivable later from the append-only `trades` table if needed) — the positions table always reflects current holdings only
- **Cash updates**: atomic with position updates (single transaction)

### Ticker Scope

- A ticker must be on the watchlist before it can be traded — `POST /api/portfolio/trade` returns 400 for a ticker not on the watchlist, since the price cache (Section 6) only tracks watched tickers. This keeps the pricing model simple: no "price any symbol on demand" logic
- `DELETE /api/watchlist/{ticker}` returns 409 while an open position exists for that ticker, so a held position's price can never go stale from being dropped out of the cache. The user must sell the position to zero before removing the ticker
- Ticker format: `^[A-Z]{1,5}$` (1-5 uppercase letters). There's no real symbol lookup in simulator mode, so this format check is the only validity rule — the simulator generates a plausible seed price for any symbol matching it

### P&L Calculations

- **Unrealized P&L per position**: `(current_price - avg_cost) * quantity`
- **Total portfolio value**: `cash_balance + sum(current_price * quantity for each position)`
- **Portfolio snapshots**: the backend periodically (e.g., every 30 seconds) records the total portfolio value to `portfolio_snapshots` for the P&L chart

---

## 15. Default Ticker Universe

The following tickers are seeded in the default watchlist and supported by the simulator:

| Ticker | Company        | Approximate Seed Price |
| ------ | -------------- | ---------------------- |
| AAPL   | Apple          | ~$190                  |
| GOOGL  | Alphabet       | ~$175                  |
| MSFT   | Microsoft      | ~$420                  |
| AMZN   | Amazon         | ~$185                  |
| TSLA   | Tesla          | ~$250                  |
| NVDA   | NVIDIA         | ~$130                  |
| META   | Meta Platforms | ~$500                  |
| JPM    | JPMorgan Chase | ~$200                  |
| V      | Visa           | ~$280                  |
| NFLX   | Netflix        | ~$630                  |

The simulator should support additional tickers beyond these 10 (generating plausible seed prices for any valid ticker symbol), so users can add tickers via the watchlist and still see simulated data.

---

## 16. Non-Goals & Constraints

These items are explicitly out of scope:

- **No authentication or multi-user support** — single user, single session
- **No options trading** — equities only
- **No limit orders** — market orders only
- **No real money** — simulated portfolio only
- **No mobile-first design** — desktop-first, responsive as a secondary concern
- **No WebSocket protocol** — SSE only for real-time data
- **No external database** — SQLite only, no Postgres/Supabase
- **No CI/CD pipeline** — Docker build + local scripts are sufficient
- **No cloud deployment** — the Docker image is portable to any container platform, but provisioning/deployment config (e.g. Terraform) is out of scope

---

## 17. Success Criteria

The project is complete when:

1. `scripts/start_mac.sh` (or the Docker command) brings up the app on port 8000
2. The watchlist loads with 10 default tickers, prices streaming and flashing
3. The user can buy and sell shares, and the portfolio updates immediately
4. The portfolio heatmap and P&L chart render correctly with live data
5. The AI chat responds with streaming text, and can execute trades and manage the watchlist via natural language
6. The simulator provides a compelling real-time experience with no external dependencies
7. Backend and frontend unit test suites pass
8. All Playwright E2E tests pass
9. The Docker image builds cleanly from a fresh clone + `.env` file

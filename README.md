# Financial APP

An AI-powered trading workstation: a Bloomberg-style dark terminal that streams live simulated market data, lets you trade a $10,000 virtual portfolio, and includes an AI chat assistant that can analyze your positions and execute trades on your behalf.

Built as a capstone project for an agentic AI coding course — the whole app was built by orchestrated Claude Code sub-agents. See `planning/PLAN.md` for the product spec and `docs/ARCHITECTURE.md` for the technical contract.

## Quick start

1. Copy `.env.example` to `.env` and fill in `OPENROUTER_API_KEY` (used for the AI chat assistant; get one at [openrouter.ai](https://openrouter.ai)).
2. Make sure Docker is running, then:

   **Windows (PowerShell):**

   ```powershell
   ./scripts/start_windows.ps1
   ```

   **macOS/Linux:**

   ```bash
   ./scripts/start_mac.sh
   ```

3. Open http://localhost:8000.

Both scripts build the Docker image on first run and are safe to re-run — they leave an already-running container alone. Stop the app with `./scripts/stop_windows.ps1` or `./scripts/stop_mac.sh` (your data in `db/` is preserved).

## What it does

- Live-streaming watchlist with flashing price updates and sparkline charts
- Buy/sell shares at the simulated live price, no fees, instant fill
- Portfolio heatmap, P&L chart, and a positions table
- An AI chat assistant that can analyze your portfolio and execute trades or manage your watchlist through natural language

No real money, no real market data by default — see `planning/PLAN.md` Section 5 for wiring in a real market data provider.

## Development

- **Backend** (`backend/`): FastAPI + Python, managed with `uv`. `uv run pytest` for unit tests.
- **Frontend** (`frontend/`): Next.js + TypeScript, static export. `npm run dev` for a hot-reloading dev server (talks to a backend running on `:8000`), `npm test` for unit tests.
- **E2E tests** (`test/`): Playwright, run via `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit`.

## Environment variables

See `.env.example`. `OPENROUTER_API_KEY` is required for the AI chat; `MASSIVE_API_KEY` is optional (real market data instead of the built-in simulator); `LLM_MOCK=true` gives deterministic canned chat responses for testing.

"""FastAPI application entrypoint. See docs/ARCHITECTURE.md Section 2 and
planning/PLAN.md Sections 3, 11.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.chat import router as chat_router
from app.db.connection import get_connection
from app.db.schema import DEFAULT_USER_ID, init_db
from app.errors import ConflictError, NotFoundError, ValidationError
from app.market_data.base import MarketDataProvider
from app.market_data.massive_client import MassiveClient
from app.market_data.simulator import MarketSimulator
from app.portfolio import record_snapshot
from app.portfolio import router as portfolio_router
from app.prices import router as prices_router
from app.schemas import HealthResponse
from app.watchlist import router as watchlist_router

load_dotenv()

logger = logging.getLogger(__name__)

SNAPSHOT_INTERVAL_SECONDS = 30.0

# backend/app/main.py -> backend/static, matching the Dockerfile's
# `COPY --from=frontend-build /app/frontend/out /app/backend/static`.
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_provider() -> MarketDataProvider:
    """planning/PLAN.md Section 5: MassiveClient if MASSIVE_API_KEY is set
    and non-empty, otherwise the built-in simulator."""
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()
    if api_key:
        return MassiveClient(api_key=api_key)
    return MarketSimulator()


async def _snapshot_loop(provider: MarketDataProvider) -> None:
    """Background task: record a portfolio_snapshots row roughly every 30s
    (planning/PLAN.md Section 14)."""
    while True:
        await asyncio.sleep(SNAPSHOT_INTERVAL_SECONDS)
        conn = get_connection()
        try:
            record_snapshot(conn, provider)
        except Exception:  # never let a snapshot failure kill the loop
            logger.exception("failed to record portfolio snapshot")
        finally:
            conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_connection()
    try:
        init_db(conn)
        tickers = [
            row["ticker"]
            for row in conn.execute(
                "SELECT ticker FROM watchlist WHERE user_id = ?", (DEFAULT_USER_ID,)
            ).fetchall()
        ]
    finally:
        conn.close()

    provider = create_provider()
    app.state.provider = provider
    for ticker in tickers:
        provider.watch(ticker)

    await provider.start()
    snapshot_task = asyncio.create_task(_snapshot_loop(provider))

    try:
        yield
    finally:
        snapshot_task.cancel()
        try:
            await snapshot_task
        except asyncio.CancelledError:
            pass
        await provider.stop()


app = FastAPI(title="Finance App Backend", lifespan=lifespan)

# Static export is same-origin in production (Section 3, PLAN.md), so this
# only matters for `next dev` (localhost:3000) talking to this server
# (localhost:8000) during frontend development. No auth/cookies exist in
# this app (Section 16), so a permissive origin list carries no real risk.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def _request_validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # docs/ARCHITECTURE.md Section 4 specifies 400 for request-shape
    # validation failures (e.g. bad ticker format on POST /api/watchlist),
    # not FastAPI's default 422 — this keeps the documented {"detail": ...}
    # shape but corrects the status code project-wide.
    return JSONResponse(status_code=400, content={"detail": jsonable_encoder(exc.errors())})


@app.exception_handler(ValidationError)
async def _validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(NotFoundError)
async def _not_found_error_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def _conflict_error_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


app.include_router(portfolio_router)
app.include_router(watchlist_router)
app.include_router(prices_router)
app.include_router(chat_router)

# Guard against the directory not existing: it won't locally until the
# Frontend Engineer's phase produces a build (`frontend/out` copied into
# backend/static by the Dockerfile). Local dev must not crash on startup.
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

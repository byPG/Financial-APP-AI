# syntax=docker/dockerfile:1
#
# Finance App — multi-stage build.
# Stage 1 builds the Next.js static export (frontend/), Stage 2 installs the
# FastAPI backend (backend/) with uv and serves the exported frontend as
# static files alongside the API on a single port (8000).
#
# See planning/PLAN.md Section 11 and docs/ARCHITECTURE.md Section 1/2.

# ---------------------------------------------------------------------------
# Stage 1: build the Next.js static export
# ---------------------------------------------------------------------------
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend

# Install dependencies first for better layer caching.
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

# Copy the rest of the frontend source and build the static export.
# next.config.ts sets output: "export", so `next build` produces frontend/out/.
COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: Python backend, serving the API + the built static frontend
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS backend

# Install uv (fast Python package/dependency manager) via the official
# distroless copy pattern — avoids curl/pip bootstrap in the final image.
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy backend project files and install dependencies from the lockfile.
# uv.lock does not exist yet in this repo (no `uv sync` has been run locally);
# once it is generated and committed, this COPY + `uv sync --frozen` pair
# will produce reproducible installs. Until then, `uv sync` (without
# --frozen) resolves from pyproject.toml and creates the lockfile in-image.
COPY backend/pyproject.toml backend/.python-version ./backend/
COPY backend/uv.lock* ./backend/

WORKDIR /app/backend
RUN if [ -f uv.lock ]; then \
        uv sync --frozen --no-dev; \
    else \
        uv sync --no-dev; \
    fi

# Copy the rest of the backend source (app code, db/ schema+seed logic, tests).
COPY backend/ ./

# Copy the built frontend static export into the directory the backend serves.
COPY --from=frontend-build /app/frontend/out /app/backend/static

# The SQLite database lives under /app/db, bind-mounted from the host's
# ./db directory (see docker-compose.yml and scripts/). The backend creates
# finally.db here lazily on first run if it doesn't already exist.
RUN mkdir -p /app/db

EXPOSE 8000

# app.main:app is the FastAPI app the Backend Engineer will create at
# backend/app/main.py (per docs/ARCHITECTURE.md Section 2). This CMD is
# correct-by-convention ahead of that file existing.
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

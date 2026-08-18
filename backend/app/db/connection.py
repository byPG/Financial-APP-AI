"""SQLite connection management. See docs/ARCHITECTURE.md Section 1 and
planning/PLAN.md Section 7 ("Concurrency & Safety": WAL mode, short
transactions — several writers hit this file: trade execution, the
portfolio-snapshot background task, and chat message persistence).

DB file location: the project's top-level ``db/`` directory
(``Financial-APP-AI/db/finally.db``), resolved relative to *this file* so it
works regardless of the process's current working directory. This mirrors
the Docker bind mount (repo ``db/`` -> ``/app/db``, see Dockerfile /
docker-compose.yml) and local (non-Docker) dev alike: this file lives at
``backend/app/db/connection.py``, four levels below the project root, so
``parents[3]`` is the project root in both environments (inside the
container that's ``/app``, since the backend's own root is copied to
``/app/backend``).

``DB_PATH`` env var overrides the resolved path. This is an internal
implementation detail (used by tests to point at an isolated tmp-path
database per test) — deliberately not documented in planning/PLAN.md's env
var list or .env.example, per the Backend Engineer task boundaries.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parents[3]
_DEFAULT_DB_PATH = _PROJECT_ROOT / "db" / "finally.db"


def get_db_path() -> Path:
    override = os.environ.get("DB_PATH")
    if override:
        return Path(override)
    return _DEFAULT_DB_PATH


def get_connection() -> sqlite3.Connection:
    """Open a new connection to the SQLite database.

    Deliberately cheap and short-lived: callers open one per request (or per
    background-task tick) and close it promptly, rather than holding a
    single shared connection open for the process lifetime. This keeps
    transactions short under WAL mode and sidesteps sqlite3's
    single-thread-affinity caveats without needing a connection pool for an
    app this size.
    """
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

"""Ensures the `app` package (backend/app/...) is importable regardless of
which directory pytest is invoked from. backend/ is not installed as a
package (pyproject.toml sets `package = false`, see docs/ARCHITECTURE.md
Section 1), so this inserts the backend/ root onto sys.path explicitly
rather than relying on pytest's default rootdir-insertion behavior.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

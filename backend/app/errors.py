"""Domain-level errors for business logic in portfolio.py / watchlist.py /
chat.py. Kept separate from HTTP concerns (status codes) so the business
logic functions stay independent of FastAPI and are easy to unit test
directly. app/main.py registers exception handlers that translate these to
the status codes docs/ARCHITECTURE.md Section 4 specifies.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all business-rule violations raised by portfolio.py,
    watchlist.py, and chat.py. Never raised directly — catch this in code
    (e.g. chat.py's per-instruction try/except) that wants to handle *any*
    business-rule failure uniformly; catch a specific subclass when the
    HTTP-facing distinction (400 vs 404 vs 409) matters.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


class ValidationError(DomainError):
    """Maps to HTTP 400. Bad ticker format, insufficient cash/shares, ticker
    not on the watchlist, etc."""


class NotFoundError(DomainError):
    """Maps to HTTP 404. E.g. removing a ticker that isn't on the watchlist."""


class ConflictError(DomainError):
    """Maps to HTTP 409. E.g. removing a ticker with an open position."""

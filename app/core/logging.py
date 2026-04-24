# Shared structured logging setup for the application.
# All modules should use get_logger(__name__) rather than print() or bare logging calls.
#
# Request ID:
#   A UUID is generated per request by RequestIDMiddleware (app/main.py) and stored
#   in a ContextVar. RequestIDFilter injects it into every log record automatically
#   so all log lines for a single request share the same request_id field.
#   Callers receive the same ID in the X-Request-ID response header.
from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

_request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIDFilter(logging.Filter):
    """Inject the current request ID into every log record as request_id."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get()  # type: ignore[attr-defined]
        return True


def set_request_id(request_id: str) -> None:
    """Set the request ID for the current async context. Called by middleware."""
    _request_id_var.set(request_id)


def new_request_id() -> str:
    """Generate a new random request ID."""
    return str(uuid.uuid4())


def configure_logging() -> None:
    """Attach RequestIDFilter to the root logger so all child loggers inherit it.

    Must be called once at app startup before any requests are handled.
    """
    root = logging.getLogger()
    if not any(isinstance(f, RequestIDFilter) for f in root.filters):
        root.addFilter(RequestIDFilter())


def get_logger(name: str) -> logging.Logger:
    """Return a named logger using the application logging config."""
    return logging.getLogger(name)

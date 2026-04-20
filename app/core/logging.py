# Shared structured logging setup for the application.
# All modules should use get_logger(__name__) rather than print() or bare logging calls.
from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    """Return a named logger using the application logging config."""
    return logging.getLogger(name)

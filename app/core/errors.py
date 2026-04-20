# Domain exception types for the application.
# Repository and service layers raise these; the API layer maps them to HTTP responses.
# Never branch on raw exception message strings; use these typed exceptions instead.
from __future__ import annotations


class NotFoundError(Exception):
    """Raised when a requested resource does not exist."""


class ConflictError(Exception):
    """Raised when an operation conflicts with existing state.

    Used for source-managed row write attempts and duplicate resource creation.
    """


class ValidationError(Exception):
    """Raised when domain-level validation fails outside of Pydantic request parsing."""

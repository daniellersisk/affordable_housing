from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorItem(BaseModel):
    """One field-level error detail (mirrors what our API returns)."""

    field: str = Field(..., examples=["sort_by", "X-API-Key"])
    message: str = Field(..., examples=["header is missing or incorrect"])


class ErrorDetail(BaseModel):
    """Structured error payload returned under the top-level `detail` key."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: list[ErrorItem] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """FastAPI error response envelope used across the API."""

    model_config = ConfigDict(extra="forbid")

    detail: ErrorDetail


def example_error_response(*, code: str, message: str, details: list[dict[str, Any]] | None = None) -> dict:
    """Helper for OpenAPI examples (keeps error shapes consistent)."""

    return {
        "detail": {
            "code": code,
            "message": message,
            "details": details or [],
        }
    }


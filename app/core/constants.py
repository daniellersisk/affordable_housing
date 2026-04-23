# Application-wide constants and enums.
# Use these instead of magic strings or numbers throughout the codebase.
from __future__ import annotations

from enum import Enum


class GeoShape(str, Enum):
    """Discriminator values for the geo filter on GET /housing-units."""

    RECTANGLE = "rectangle"
    CIRCLE = "circle"


SOURCE_IDENTITY_CONSTRAINT = "uq_housing_units_project_building"


class ErrorCode(str, Enum):
    """Structured error codes returned in API error payloads."""

    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    INVALID_GEO_FILTER = "INVALID_GEO_FILTER"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    INTERNAL_ERROR = "INTERNAL_ERROR"

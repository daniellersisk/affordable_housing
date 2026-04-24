# Application-wide constants and enums.
# Use these instead of magic strings or numbers throughout the codebase.
from __future__ import annotations

from enum import Enum


class GeoShape(str, Enum):
    """Discriminator values for the geo filter on GET /housing-units."""

    RECTANGLE = "rectangle"
    CIRCLE = "circle"


class Borough(str, Enum):
    """Valid NYC borough values."""

    MANHATTAN = "MANHATTAN"
    BROOKLYN = "BROOKLYN"
    QUEENS = "QUEENS"
    BRONX = "BRONX"
    STATEN_ISLAND = "STATEN ISLAND"


SOURCE_IDENTITY_CONSTRAINT = "uq_housing_units_project_building"
SOCRATA_ROW_IDENTITY_CONSTRAINT = "uq_housing_units_socrata_row_id"


class SortField(str, Enum):
    """Sortable fields for GET /v1/housing-units."""

    ID = "id"
    NUM_UNITS = "num_units"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    STREET_NAME = "street_name"


class SortOrder(str, Enum):
    """Sort direction for list endpoints."""

    ASC = "asc"
    DESC = "desc"


class ErrorCode(str, Enum):
    """Structured error codes returned in API error payloads."""

    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    INVALID_GEO_FILTER = "INVALID_GEO_FILTER"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    INTERNAL_ERROR = "INTERNAL_ERROR"

from app.schemas.error import ErrorDetail, ErrorItem, ErrorResponse

__all__ = [
    "ErrorDetail",
    "ErrorItem",
    "ErrorResponse",
]
# Package marker for Pydantic request and response schemas.
# Schemas define the API surface; ORM models define the storage shape.
# Keep these separate so framework and persistence concerns do not bleed together.

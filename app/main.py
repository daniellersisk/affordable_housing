# Application entry point.
# Creates the FastAPI app and registers all route modules.
# Keep this file thin: no business logic, no inline route handlers.
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import analytics, health, housing_units
from app.core.constants import ErrorCode

app = FastAPI(
    title="Housing Units API",
    description="nyc affordable housing units — queryable by borough, geo, and unit count.",
    version="0.1.0",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Map all Pydantic/FastAPI 422 validation errors to our structured error format."""
    first = exc.errors()[0] if exc.errors() else {}
    msg = str(first.get("msg", "validation error")).removeprefix("Value error, ")
    field = ".".join(str(loc) for loc in first.get("loc", []) if loc not in ("body", "query"))
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "code": ErrorCode.VALIDATION_ERROR,
                "message": msg,
                "details": [{"field": field, "message": msg}] if field else [],
            }
        },
    )


app.include_router(health.router)
app.include_router(housing_units.public_router)
app.include_router(housing_units.private_router)
app.include_router(analytics.router)

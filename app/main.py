# Application entry point.
# Creates the FastAPI app and registers all route modules.
# Keep this file thin: no business logic, no inline route handlers.
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import analytics, health, housing_units
from app.core.constants import ErrorCode
from app.core.logging import configure_logging, new_request_id, set_request_id

configure_logging()

app = FastAPI(
    title="Housing Units API",
    description="nyc affordable housing units — queryable by borough, geo, and unit count.",
    version="0.1.0",
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next: object) -> object:
    """Generate a request ID for every request and propagate it through logs and response.

    Honours an incoming X-Request-ID header so callers can inject their own correlation ID
    (useful when this API sits behind a gateway that already assigns trace IDs).
    """
    request_id = request.headers.get("X-Request-ID") or new_request_id()
    set_request_id(request_id)
    response = await call_next(request)  # type: ignore[operator]
    response.headers["X-Request-ID"] = request_id
    return response


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

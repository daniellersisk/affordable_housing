# Application entry point.
# Creates the FastAPI app and registers all route modules.
# Keep this file thin: no business logic, no inline route handlers.
from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import health, housing_units

app = FastAPI(title="Housing Units API")

app.include_router(health.router)
app.include_router(housing_units.router)

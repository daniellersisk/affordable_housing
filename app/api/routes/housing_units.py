# Route handlers for the /housing-units resource.
# Handlers are thin: validate input, call the service layer, return responses.
# Auth dependency will be applied to write routes (POST, PUT, DELETE) in Step 7.
# Step 5 will implement the full handler bodies once schemas and services exist.
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/housing-units", tags=["housing-units"])


# TODO: Step 5 - GET /housing-units with filter query params
# TODO: Step 5 - GET /housing-units/{id}
# TODO: Step 5 - POST /housing-units (auth required)
# TODO: Step 5 - PUT /housing-units/{id} (auth required)
# TODO: Step 5 - DELETE /housing-units/{id} (auth required)

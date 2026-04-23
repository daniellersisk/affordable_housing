"""E2E test fixtures.

E2E tests use the same TestClient from the root conftest.
They exercise full HTTP lifecycle flows — create, read, update, delete —
never instantiating services or repositories directly.
"""
from __future__ import annotations

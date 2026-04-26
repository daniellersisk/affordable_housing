"""E2E test fixtures.

E2E tests call the API over real HTTP.

In CI we run `pytest -m e2e` inside the API container without separately starting
the `api` service, so this fixture starts a local uvicorn process for the
duration of the test session and uses `httpx` to call it.
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import time
from collections.abc import Iterator

import httpx
import pytest

from app.settings import settings


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="session")
def e2e_base_url() -> Iterator[str]:
    """Base URL for a running uvicorn instance."""
    # Allow overriding for local runs against `docker compose up api`.
    env_url = os.getenv("E2E_BASE_URL")
    if env_url:
        yield env_url.rstrip("/")
        return

    port = _pick_free_port()
    base_url = f"http://127.0.0.1:{port}"

    proc = subprocess.Popen(
        [
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        deadline = time.time() + 20
        with httpx.Client(base_url=base_url, timeout=2.0) as http:
            while True:
                try:
                    resp = http.get("/health")
                    if resp.status_code == 200:
                        break
                except Exception:
                    pass
                if time.time() > deadline:
                    output = ""
                    if proc.stdout is not None:
                        output = proc.stdout.read() or ""
                    raise RuntimeError(f"uvicorn failed to start.\n{output}")
                time.sleep(0.2)

        yield base_url
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


@pytest.fixture
def e2e_http(e2e_base_url: str) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=e2e_base_url, timeout=10.0) as client:
        yield client


@pytest.fixture
def e2e_auth_headers() -> dict[str, str]:
    return {settings.write_api_key_header: settings.write_api_key}


@pytest.fixture
def e2e_created_unit_ids() -> list[int]:
    """Track created ids so tests can clean up."""
    return []

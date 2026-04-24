# HTTP client for the NYC Open Data Socrata API.
# All ingestion requests go through this client — no other module may call Socrata directly.
# Uses HTTP POST to query.json with SoQL; handles pagination, retries, and app-token auth.
# Config values come from settings only — nothing is hardcoded here.
from __future__ import annotations

import time
from collections.abc import Iterator

import httpx

from app.core.logging import get_logger
from app.settings import Settings, settings

logger = get_logger(__name__)

# Retry back-off base in seconds: attempt 1 → 1s, attempt 2 → 2s, attempt 3 → 4s.
_BACKOFF_BASE = 1


class SocrataClient:
    """Paginated Socrata SODA client for the NYC affordable-housing dataset."""

    def __init__(self, cfg: Settings) -> None:
        self._url = cfg.resolved_open_data_url
        self._page_size = cfg.ingest_page_size
        self._timeout = cfg.ingest_timeout_seconds
        self._max_retries = cfg.ingest_max_retries
        # Build headers once; app token must not appear in logs anywhere.
        self._headers: dict[str, str] = {"Accept": "application/json"}
        if cfg.soda_app_token:
            self._headers["X-App-Token"] = cfg.soda_app_token

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_all(self) -> Iterator[list[dict]]:
        """Yield pages of records until Socrata returns an empty page.

        Stops early if the last page was shorter than the configured page
        size, which means there are no more records.
        """
        offset = 0
        while True:
            page = self._fetch_page(offset, self._page_size)
            if not page:
                logger.info("socrata pagination complete", extra={"offset": offset})
                break
            yield page
            if len(page) < self._page_size:
                logger.info("socrata last page reached", extra={"offset": offset, "count": len(page)})
                break
            offset += self._page_size

    def get_by_source_id(self, project_id: str, building_id: str) -> dict | None:
        """Fetch a single record by source composite identity.

        Returns None if Socrata has no matching record.
        Single quotes in project_id/building_id are escaped to prevent SoQL injection.
        """
        safe_pid = _escape_soql(project_id)
        safe_bid = _escape_soql(building_id)
        where = f"project_id='{safe_pid}' AND building_id='{safe_bid}'"
        results = self._get({"$where": where, "$limit": "1"})
        return results[0] if results else None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_page(self, offset: int, limit: int) -> list[dict]:
        logger.info("socrata fetch page", extra={"offset": offset, "limit": limit})
        return self._get({"$limit": str(limit), "$offset": str(offset), "$order": ":id"})

    def _get(self, params: dict[str, str]) -> list[dict]:
        """GET the resource endpoint with the given query params.

        Retries up to max_retries times with exponential back-off on
        transient HTTP or network errors.  Raises on permanent failure.
        """
        for attempt in range(1, self._max_retries + 1):
            try:
                response = httpx.get(
                    self._url,
                    params=params,
                    headers=self._headers,
                    timeout=float(self._timeout),
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                logger.warning(
                    "socrata http error",
                    extra={"attempt": attempt, "status": status},
                )
                if attempt == self._max_retries or status < 500:
                    raise
            except httpx.RequestError as exc:
                logger.warning(
                    "socrata request error",
                    extra={"attempt": attempt, "error": type(exc).__name__},
                )
                if attempt == self._max_retries:
                    raise
            time.sleep(_BACKOFF_BASE * (2 ** (attempt - 1)))
        return []  # unreachable — loop always raises or returns above


def _escape_soql(value: str) -> str:
    """Escape single quotes in a SoQL string literal by doubling them."""
    return value.replace("'", "''")


# Module-level singleton — one client per process, config from settings.
# Tests patch this name to avoid real HTTP calls.
socrata_client = SocrataClient(settings)

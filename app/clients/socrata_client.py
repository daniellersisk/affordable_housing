# HTTP client for the NYC Open Data Socrata API.
# All ingestion requests to the Socrata dataset API go through this client.
# Uses POST to query.json endpoints; handles pagination, retries, and app token auth.
# Config values (token, page size, timeout, retries) come from settings, not hardcoded.
# Step 6 will implement the full client with pagination and retry logic.
from __future__ import annotations

# TODO: Step 6 - implement SocrataClient with:
#   __init__(settings) to configure base URL, view ID, app token, timeout, retries
#   fetch_page(offset, limit) -> list[dict] using HTTP POST to query.json
#   get_all() -> Iterator[list[dict]] using paginated fetch_page calls

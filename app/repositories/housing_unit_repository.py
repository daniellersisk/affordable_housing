# repository for housing_units table access.
# all database queries for housing units live here.
# raises domain errors from app.core.errors, never raw sqlalchemy exceptions.
from __future__ import annotations

# flush() sends sql to the db but doesn't commit — changes live in the transaction
# and are visible in the same session. commit() makes them permanent.
# we flush once per logical operation so sqlalchemy batches all dirty fields
# into a single update instead of one round trip per field change.
# the route handler owns commit/rollback; the repo just flushes.

# TODO: Step 4 - implement get_by_id(session, id) -> HousingUnit | None
# TODO: Step 4 - implement list_with_filters(session, filters) -> list[HousingUnit]
# TODO: Step 4 - implement create(session, data) -> HousingUnit
# TODO: Step 4 - implement update(session, id, data) -> HousingUnit
# TODO: Step 4 - implement delete(session, id) -> None
# TODO: Step 4 - implement upsert_from_source(session, records) -> int for ingestion

# Bulk ETL script — fetches all records from the Socrata dataset and upserts them.
# Run after migrations:
#   docker compose run --rm api python -m app.scripts.import_nyc_data
#
# Dry-run mode (no DB writes, first page only):
#   docker compose run --rm api python -m app.scripts.import_nyc_data --dry-run
#
# Idempotent: re-running does not duplicate records — upsert merges on
# Socrata system id (":id") stored as socrata_row_id. Each page is committed independently so a
# mid-run failure leaves already-processed pages intact.
from __future__ import annotations

import sys

from app.clients.socrata_client import SocrataClient
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.repositories import housing_unit_repository as repo
from app.settings import settings

logger = get_logger(__name__)

_DRY_RUN_PREVIEW_COUNT = 3


def main(dry_run: bool = False) -> None:
    client = SocrataClient(settings)

    logger.info(
        "import started",
        extra={"url": settings.resolved_open_data_url, "dry_run": dry_run},
    )

    if dry_run:
        _run_dry(client)
        return

    session = SessionLocal()
    total_upserted = 0
    total_received = 0
    total_skipped = 0
    pages_processed = 0
    errors = 0

    try:
        for page in client.get_all():
            pages_processed += 1
            received = len(page)
            total_received += received
            try:
                count = repo.upsert_from_source(session, page)
                session.commit()
                total_upserted += count
                skipped = received - count
                total_skipped += skipped
                logger.info(
                    "page committed",
                    extra={
                        "page": pages_processed,
                        "received": received,
                        "upserted": count,
                        "skipped": skipped,
                        "total_upserted": total_upserted,
                    },
                )
            except Exception as exc:
                session.rollback()
                errors += 1
                logger.error(
                    "page failed",
                    extra={"page": pages_processed, "error": str(exc)},
                )
    except Exception as exc:
        logger.error("import aborted", extra={"error": str(exc)})
        sys.exit(1)
    finally:
        session.close()

    logger.info(
        "import complete",
        extra={
            "pages": pages_processed,
            "total_received": total_received,
            "total_upserted": total_upserted,
            "total_skipped": total_skipped,
            "errors": errors,
        },
    )

    if errors:
        sys.exit(1)


def _run_dry(client: SocrataClient) -> None:
    """Fetch first page only, log field mapping and sample records — no DB writes."""
    logger.info(
        "dry run started",
        extra={
            "url": settings.resolved_open_data_url,
            "page_size": settings.ingest_page_size,
            "app_token_set": bool(settings.soda_app_token),
        },
    )

    try:
        page = client._fetch_page(0, settings.ingest_page_size)
    except Exception as exc:
        logger.error("dry run fetch failed", extra={"error": str(exc)})
        sys.exit(1)

    if not page:
        logger.info("dry run received 0 records")
        sys.exit(0)

    logger.info("dry run fetched first page", extra={"records": len(page)})

    first = page[0]
    for key, value in sorted(first.items()):
        logger.info("dry run raw source field", extra={"field": key, "value": repr(value)})

    mapping = {
        "total_units": "num_units (int cast)",
        "reporting_construction_type": "construction_type",
        "borough": "borough (uppercased)",
    }
    for src, dst in mapping.items():
        present = "✓ present" if src in first else "— not in this record"
        logger.info(
            "dry run field mapping",
            extra={"source_field": src, "mapped_to": dst, "present": present},
        )

    for i, rec in enumerate(page[:_DRY_RUN_PREVIEW_COUNT], 1):
        logger.info(
            "dry run sample record",
            extra={
                "i": i,
                "socrata_row_id": rec.get(":id"),
                "project_id": rec.get("project_id"),
                "building_id": rec.get("building_id"),
                "total_units": rec.get("total_units"),
                "borough": rec.get("borough"),
                "street_name": rec.get("street_name"),
            },
        )

    logger.info("dry run complete")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)

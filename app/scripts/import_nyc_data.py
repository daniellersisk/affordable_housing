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
    print("=== DRY RUN — no data will be written to the database ===")
    print(f"Socrata URL: {settings.resolved_open_data_url}")
    print(f"Page size  : {settings.ingest_page_size}")
    print(f"App token  : {'set' if settings.soda_app_token else 'NOT SET (rate limits apply)'}")
    print()

    try:
        page = client._fetch_page(0, settings.ingest_page_size)
    except Exception as exc:
        print(f"ERROR: could not fetch from Socrata — {exc}")
        sys.exit(1)

    if not page:
        print("Socrata returned 0 records. Check the dataset ID and URL.")
        sys.exit(0)

    print(f"First page returned {len(page)} records.")
    print()

    first = page[0]
    print("--- Raw source fields (first record) ---")
    for key, value in sorted(first.items()):
        print(f"  {key}: {value!r}")

    print()
    print("--- Field mapping applied at write time ---")
    mapping = {
        "total_units": "num_units (int cast)",
        "reporting_construction_type": "construction_type",
        "borough": "borough (uppercased)",
    }
    for src, dst in mapping.items():
        present = "✓ present" if src in first else "— not in this record"
        print(f"  {src} → {dst}  [{present}]")

    print()
    print(f"--- Sample records (first {_DRY_RUN_PREVIEW_COUNT}) ---")
    for i, rec in enumerate(page[:_DRY_RUN_PREVIEW_COUNT], 1):
        print(
            f"  [{i}] socrata_row_id={rec.get(':id')!r}"
            f"  project_id={rec.get('project_id')!r}"
            f"  building_id={rec.get('building_id')!r}"
            f"  total_units={rec.get('total_units')!r}"
            f"  borough={rec.get('borough')!r}"
            f"  street_name={rec.get('street_name')!r}"
        )

    print()
    print("=== Dry run complete — re-run without --dry-run to import ===")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)

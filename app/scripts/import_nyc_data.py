# Bulk ETL script — fetches all records from the Socrata dataset and upserts them.
# Run after migrations:
#   docker compose run --rm api python -m app.scripts.import_nyc_data
#
# Idempotent: re-running does not duplicate records — upsert merges on
# (project_id, building_id). Each page is committed independently so a
# mid-run failure leaves already-processed pages intact.
from __future__ import annotations

import sys

from app.clients.socrata_client import SocrataClient
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.repositories import housing_unit_repository as repo
from app.settings import settings

logger = get_logger(__name__)


def main() -> None:
    client = SocrataClient(settings)
    session = SessionLocal()

    total_upserted = 0
    pages_processed = 0
    errors = 0

    logger.info("import started", extra={"url": settings.resolved_open_data_url})

    try:
        for page in client.get_all():
            pages_processed += 1
            try:
                count = repo.upsert_from_source(session, page)
                session.commit()
                total_upserted += count
                logger.info(
                    "page committed",
                    extra={"page": pages_processed, "records": count, "total": total_upserted},
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
        extra={"pages": pages_processed, "total_upserted": total_upserted, "errors": errors},
    )

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()

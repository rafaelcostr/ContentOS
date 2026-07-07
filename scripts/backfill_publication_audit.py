import asyncio
import json
import os
import uuid

from sqlalchemy import text

from contentos_database.platform_publications import (
    list_platform_publications,
    persist_platform_publications,
)
from contentos_database.session import get_session_factory, init_db

PIPELINE_ID = uuid.UUID("2ddbfa11-a846-48c0-bc6f-647f65ead560")
PROJECT_ID = uuid.UUID("ca8d7510-2fb4-407f-a92c-b402d4e6ae78")


async def main() -> None:
    init_db(os.environ["DATABASE_URL"])
    session_factory = get_session_factory()
    if session_factory is None:
        raise RuntimeError("session factory unavailable")

    async with session_factory() as db:
        row = (
            await db.execute(
                text(
                    "SELECT output_data::text "
                    "FROM jobs WHERE pipeline_id = :pipeline_id AND step = 'publisher'"
                ),
                {"pipeline_id": str(PIPELINE_ID)},
            )
        ).first()
    if not row:
        print("publisher job not found")
        return

    project_id = PROJECT_ID
    data = json.loads(row[0])
    publication = data.get("publication") or {}
    platforms = publication.get("platforms") or data.get("platform_publications") or {}
    mode = publication.get("mode") or data.get("mode") or "dry_run"

    count = await persist_platform_publications(project_id, PIPELINE_ID, mode, platforms)
    rows = await list_platform_publications(project_id, pipeline_id=PIPELINE_ID)
    print(f"persisted={count} listed={len(rows)}")
    for row in rows:
        print(row.platform, row.status, row.publish_url)


if __name__ == "__main__":
    asyncio.run(main())

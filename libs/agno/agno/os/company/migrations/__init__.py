"""Explicit, transactional Company migrations; never invoked by server startup."""

import asyncio
from typing import Any

from sqlalchemy import text

VERSION = 5


def migrate(db: Any) -> None:
    """Apply pending versions with an exclusive database migration lock."""
    from agno.os.company.config import CompanyConfig
    from agno.os.company.migrations.initial import SQL as INITIAL_SQL

    CompanyConfig(db=db)
    with db.db_engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(741927103)"))
        exists = conn.execute(text("SELECT to_regclass('agno_company.schema_version')")).scalar()
        if exists is None:
            conn.exec_driver_sql(INITIAL_SQL)
            version = 5
        else:
            version = conn.execute(text("SELECT max(version) FROM agno_company.schema_version")).scalar()
        if version != VERSION:
            raise RuntimeError(
                "Unsupported Company prototype schema; upgrade with its original migration tooling or use a fresh database. No data was changed"
            )


async def amigrate(db: Any) -> None:
    await asyncio.to_thread(migrate, db)

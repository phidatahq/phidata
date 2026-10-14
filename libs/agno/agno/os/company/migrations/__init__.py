"""Explicit, transactional Company migrations; never invoked by server startup."""

import asyncio
from typing import Any

from sqlalchemy import text

VERSION = 6


def migrate(db: Any) -> None:
    """Apply pending versions with an exclusive database migration lock."""
    from agno.os.company.config import CompanyConfig
    from agno.os.company.migrations.v001 import SQL as INITIAL_SQL
    from agno.os.company.migrations.v002 import SQL as KEY_SQL
    from agno.os.company.migrations.v003 import SQL as WORK_SQL
    from agno.os.company.migrations.v004 import SQL as RUN_SQL
    from agno.os.company.migrations.v005 import SQL as CANCEL_SQL
    from agno.os.company.migrations.v006 import SQL as AUTOMATION_SQL

    CompanyConfig(db=db)
    with db.db_engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(741927103)"))
        exists = conn.execute(text("SELECT to_regclass('agno_company.schema_version')")).scalar()
        if exists is None:
            conn.exec_driver_sql(INITIAL_SQL)
            version = 1
        else:
            version = conn.execute(text("SELECT max(version) FROM agno_company.schema_version")).scalar()
        if version == 1:
            conn.exec_driver_sql(KEY_SQL)
            version = 2
        if version == 2:
            conn.exec_driver_sql(WORK_SQL)
            version = 3
        if version == 3:
            conn.exec_driver_sql(RUN_SQL)
            version = 4
        if version == 4:
            conn.exec_driver_sql(CANCEL_SQL)
            version = 5
        if version == 5:
            conn.exec_driver_sql(AUTOMATION_SQL)
            version = 6
        if version != VERSION:
            raise RuntimeError("Unsupported Company schema version; use the matching release migration")


async def amigrate(db: Any) -> None:
    await asyncio.to_thread(migrate, db)

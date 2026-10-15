"""Explicit, transactional Company migrations; never invoked by server startup."""

import asyncio
from typing import Any

from sqlalchemy import text

VERSION = 9


def migrate(db: Any) -> None:
    """Apply pending versions with an exclusive database migration lock."""
    from agno.os.company.config import CompanyConfig
    from agno.os.company.migrations.initial import SQL as INITIAL_SQL
    from agno.os.company.migrations.v006 import SQL as AUTOMATION_SQL
    from agno.os.company.migrations.v007 import SQL as REPOSITORY_SQL

    if db is None:
        raise ValueError("Pass the resolved Company PostgreSQL database to migrate")
    CompanyConfig(db=db)
    with db.db_engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(741927103)"))
        exists = conn.execute(text("SELECT to_regclass('agno_company.schema_version')")).scalar()
        if exists is None:
            conn.exec_driver_sql(INITIAL_SQL)
            version = 5
        else:
            version = conn.execute(text("SELECT max(version) FROM agno_company.schema_version")).scalar()
        if version == 5:
            conn.exec_driver_sql(AUTOMATION_SQL)
            version = 6
        if version == 6:
            conn.exec_driver_sql(REPOSITORY_SQL)
            version = 7
        if version == 7:
            from agno.fs.db import DbFileSystem

            files = DbFileSystem(db=db, db_schema="agno_company", table_name="files")
            files.metadata.create_all(conn)
            conn.exec_driver_sql("ALTER TABLE agno_company.activity ALTER COLUMN product_id DROP NOT NULL")
            conn.exec_driver_sql("INSERT INTO agno_company.schema_version(version) VALUES (8)")
            version = 8
        if version == 8:
            conn.exec_driver_sql("ALTER TABLE agno_company.tasks DROP CONSTRAINT task_stage")
            conn.exec_driver_sql(
                "UPDATE agno_company.tasks SET schedule=NULL,schedule_principal=NULL WHERE project_id IS NOT NULL"
            )
            conn.exec_driver_sql(
                "UPDATE agno_company.tasks SET status='backlog' WHERE status IS NULL AND schedule IS NULL"
            )
            conn.exec_driver_sql("""ALTER TABLE agno_company.tasks ADD CONSTRAINT task_stage CHECK (
                (schedule IS NOT NULL AND project_id IS NULL AND status IS NULL) OR
                (schedule IS NULL AND status IS NOT NULL AND status IN ('backlog','ready','in_progress','in_review','done'))
            )""")
            conn.exec_driver_sql("INSERT INTO agno_company.schema_version(version) VALUES (9)")
            version = 9
        if version != VERSION:
            raise RuntimeError(
                "Unsupported Company prototype schema; upgrade with its original migration tooling or use a fresh database. No data was changed"
            )


async def amigrate(db: Any) -> None:
    await asyncio.to_thread(migrate, db)

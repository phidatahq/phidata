"""Add Task checkout metadata and retire the unused engineering executor value."""

import time
from typing import Any

from sqlalchemy import MetaData, Table, inspect, select, text

from agno.db.base import AsyncBaseDb, BaseDb
from agno.db.migrations.utils import quote_db_identifier


def _migrate(connection: Any, table_name: str, schema: Any = None) -> bool:
    inspector = inspect(connection)
    if not inspector.has_table(table_name, schema=schema):
        return False
    qualified = quote_db_identifier(connection.dialect.name, table_name)
    if schema:
        qualified = quote_db_identifier(connection.dialect.name, schema) + "." + qualified
    if "metadata" not in {column["name"] for column in inspector.get_columns(table_name, schema=schema)}:
        kind = "JSONB" if connection.dialect.name == "postgresql" else "JSON"
        connection.execute(text(f"ALTER TABLE {qualified} ADD COLUMN metadata {kind}"))
    table = Table(table_name, MetaData(), schema=schema, autoload_with=connection)
    rows = connection.execute(select(table).where(table.c.executor_type == "engineering")).mappings().all()
    now = int(time.time())
    for row in rows:
        history = [
            *(row["transitions"] or []),
            {
                "from": row["status"],
                "target": "backlog",
                "reason": "Retired engineering executor; select a registered executor",
                "user_id": None,
                "created_at": now,
            },
        ]
        connection.execute(
            table.update()
            .where(table.c.id == row["id"], table.c.executor_type == "engineering")
            .values(
                executor_type=None,
                executor_id=None,
                status="backlog",
                accepted_by=None,
                accepted_at=None,
                transitions=history,
                updated_at=now,
            )
        )
    return True


def up(db: BaseDb, table_type: str, table_name: str) -> bool:
    if table_type != "tasks" or type(db).__name__ not in {"PostgresDb", "SqliteDb"}:
        return False
    with getattr(db, "db_engine").begin() as connection:
        return _migrate(connection, table_name, getattr(db, "db_schema", None))


async def async_up(db: AsyncBaseDb, table_type: str, table_name: str) -> bool:
    if table_type != "tasks" or type(db).__name__ not in {"AsyncPostgresDb", "AsyncSqliteDb"}:
        return False
    async with getattr(db, "db_engine").begin() as connection:
        return await connection.run_sync(lambda conn: _migrate(conn, table_name, getattr(db, "db_schema", None)))


def down(db: BaseDb, table_type: str, table_name: str) -> bool:
    # The retired executor cannot be reconstructed. Keep the nullable metadata column.
    return False


async def async_down(db: AsyncBaseDb, table_type: str, table_name: str) -> bool:
    return False

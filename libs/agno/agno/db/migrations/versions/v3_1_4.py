"""Add Task execution references, evidence and results through shared migrations."""

from typing import Any

from sqlalchemy import Column, MetaData, Table, inspect
from sqlalchemy.schema import CreateColumn, CreateIndex

from agno.db.base import AsyncBaseDb, BaseDb


def _migrate(connection: Any, db: Any, table_name: str, revert: bool = False) -> bool:
    schema = getattr(db, "db_schema", None) if connection.dialect.name == "postgresql" else None
    inspector = inspect(connection)
    if not inspector.has_table(table_name, schema=schema):
        return False
    if connection.dialect.name == "postgresql":
        from agno.db.postgres.schemas import TASKS_TABLE_SCHEMA
    else:
        from agno.db.sqlite.schemas import TASKS_TABLE_SCHEMA
    names = ("session_id", "job_id", "evidence", "result")
    table = Table(table_name, MetaData(), schema=schema)
    for name in names:
        definition: Any = TASKS_TABLE_SCHEMA[name]
        table.append_column(Column(name, definition["type"], nullable=True, index=definition.get("index", False)))
    existing = {column["name"] for column in inspector.get_columns(table_name, schema=schema)}
    quote = connection.dialect.identifier_preparer.quote
    qualified = connection.dialect.identifier_preparer.format_table(table)
    changed = False
    for column in table.columns:
        if revert:
            if column.name in existing:
                connection.exec_driver_sql(f"ALTER TABLE {qualified} DROP COLUMN {quote(column.name)}")
                changed = True
        elif column.name not in existing:
            ddl = str(CreateColumn(column).compile(dialect=connection.dialect))
            connection.exec_driver_sql(f"ALTER TABLE {qualified} ADD COLUMN {ddl}")
            changed = True
    if not revert:
        indexes = {index["name"] for index in inspector.get_indexes(table_name, schema=schema)}
        for index in table.indexes:
            if index.name not in indexes:
                connection.execute(CreateIndex(index))
                changed = True
    return changed


def up(db: BaseDb, table_type: str, table_name: str) -> bool:
    if table_type != "tasks" or type(db).__name__ not in {"PostgresDb", "SqliteDb"}:
        return False
    with db.db_engine.begin() as connection:  # type: ignore[attr-defined]
        return _migrate(connection, db, table_name)


async def async_up(db: AsyncBaseDb, table_type: str, table_name: str) -> bool:
    if table_type != "tasks" or type(db).__name__ not in {"AsyncPostgresDb", "AsyncSqliteDb"}:
        return False
    async with db.db_engine.begin() as connection:  # type: ignore[attr-defined]
        return await connection.run_sync(lambda conn: _migrate(conn, db, table_name))


def down(db: BaseDb, table_type: str, table_name: str) -> bool:
    # Retain Task evidence/results on downgrade, like retained legacy run data.
    return False


async def async_down(db: AsyncBaseDb, table_type: str, table_name: str) -> bool:
    return False

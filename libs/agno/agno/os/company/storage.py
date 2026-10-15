"""Company-owned PostgreSQL and SQLite tables. Construction never accesses the database."""

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, List, Optional, Union

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    inspect,
    select,
    text,
)
from sqlalchemy.engine import Connection, Dialect
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.schema import CreateSchema
from sqlalchemy.types import TypeDecorator

from agno.db.postgres import PostgresDb
from agno.db.sqlite import SqliteDb


class CompanySchemaError(RuntimeError):
    """Company storage needs explicit initialization or a supported schema."""


class _UTCDateTime(TypeDecorator[datetime]):
    """Keep UTC timestamps timezone-aware when SQLite returns naive datetimes."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value: Optional[datetime], dialect: Dialect) -> Optional[datetime]:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class ProductStorage:
    def __init__(self, db: Union[PostgresDb, SqliteDb]):
        self.engine = db.db_engine
        self.schema = db.db_schema if isinstance(db, PostgresDb) else None
        self.metadata = MetaData(schema=self.schema)
        self.version = Table("company_schema_version", self.metadata, Column("version", Integer, primary_key=True))
        self.products = Table(
            "company_products",
            self.metadata,
            Column("id", String(36), primary_key=True),
            Column("name", String(200), nullable=False),
            Column("purpose", Text, nullable=False),
            Column("owner_id", Text, nullable=False),
            Column("version", Integer, nullable=False),
            Column("created_at", _UTCDateTime(), nullable=False),
            Column("updated_at", _UTCDateTime(), nullable=False),
            CheckConstraint("version >= 1", name="company_product_positive_version"),
            Index("company_products_owner_id_id", "owner_id", "id"),
        )

    @contextmanager
    def _write(self) -> Iterator[Connection]:
        with self.engine.connect() as connection:
            # SQLite has no row locks. Acquire its writer lock before reading the
            # version, and explicitly begin so DDL is transactional as well.
            if self.engine.dialect.name == "sqlite":
                connection.exec_driver_sql("BEGIN IMMEDIATE")
            else:
                connection.begin()
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def _initialize(self) -> None:
        with self._write() as connection:
            if self.schema is not None:
                # Serialize PostgreSQL initializers across processes.
                connection.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                    {"key": f"agno.company.schema:{self.schema}"},
                )
            inspector = inspect(connection)
            existing = (
                set(inspector.get_table_names(schema=self.schema))
                if self.schema is None or inspector.has_schema(self.schema)
                else set()
            )
            company_tables = {name for name in existing if name.startswith("company_")}
            if company_tables:
                if company_tables != {"company_schema_version", "company_products"}:
                    raise CompanySchemaError(
                        "Unrecognized Company tables; use a separate database or schema. No tables were changed."
                    )
                self._check_version(connection)
                return
            if self.schema is not None:
                connection.execute(CreateSchema(self.schema, if_not_exists=True))
            self.metadata.create_all(connection)
            connection.execute(self.version.insert().values(version=1))

    def _check_version(self, connection: Connection) -> None:
        try:
            versions: List[int] = list(connection.execute(select(self.version.c.version)).scalars())
        except (ProgrammingError, OperationalError) as exc:
            if (
                getattr(exc.orig, "sqlstate", getattr(exc.orig, "pgcode", None)) == "42P01"
                or self.engine.dialect.name == "sqlite"
                and "no such table: company_schema_version" in str(exc.orig)
            ):
                raise CompanySchemaError(
                    "Initialize Company explicitly with company.initialize_schema() first."
                ) from exc
            raise
        if versions != [1]:
            raise CompanySchemaError("Unsupported Company schema version; no automatic migration is performed.")

"""Company-owned PostgreSQL tables. Construction never accesses the database."""

from typing import List

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
from sqlalchemy.engine import Connection
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.schema import CreateSchema

from agno.db.postgres import PostgresDb


class CompanySchemaError(RuntimeError):
    """Company storage needs explicit initialization or a supported schema."""


class ProductStorage:
    def __init__(self, db: PostgresDb):
        self.engine = db.db_engine
        self.schema = db.db_schema
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
            Column("created_at", DateTime(timezone=True), nullable=False),
            Column("updated_at", DateTime(timezone=True), nullable=False),
            CheckConstraint("version >= 1", name="company_product_positive_version"),
            Index("company_products_owner_id_id", "owner_id", "id"),
        )

    def _initialize(self) -> None:
        with self.engine.begin() as connection:
            # Serialize initializers across processes; DDL and the marker commit together.
            connection.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                {"key": f"agno.company.schema:{self.schema}"},
            )
            inspector = inspect(connection)
            existing = (
                set(inspector.get_table_names(schema=self.schema)) if inspector.has_schema(self.schema) else set()
            )
            company_tables = {name for name in existing if name.startswith("company_")}
            if company_tables:
                if company_tables != {"company_schema_version", "company_products"}:
                    raise CompanySchemaError(
                        "Unrecognized Company tables; use a separate schema. No tables were changed."
                    )
                self._check_version(connection)
                return
            connection.execute(CreateSchema(self.schema, if_not_exists=True))
            self.metadata.create_all(connection)
            connection.execute(self.version.insert().values(version=1))

    def _check_version(self, connection: Connection) -> None:
        try:
            versions: List[int] = list(connection.execute(select(self.version.c.version)).scalars())
        except ProgrammingError as exc:
            if getattr(exc.orig, "sqlstate", getattr(exc.orig, "pgcode", None)) == "42P01":
                raise CompanySchemaError(
                    "Initialize Company explicitly with company.initialize_schema() first."
                ) from exc
            raise
        if versions != [1]:
            raise CompanySchemaError("Unsupported Company schema version; no automatic migration is performed.")

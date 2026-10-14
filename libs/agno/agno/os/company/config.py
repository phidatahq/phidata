from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CompanyConfig:
    """Explicit Company database. PostgreSQL is the supported adapter.

    The service borrows its engine but owns the ``agno_company`` schema. Apply
    migrations explicitly before serving; constructing this config never connects.
    """

    db: Any

    def __post_init__(self) -> None:
        from agno.db.postgres import PostgresDb

        if not isinstance(self.db, PostgresDb) or self.db.db_engine.dialect.name != "postgresql":
            raise ValueError("CompanyConfig requires a synchronous PostgresDb; other adapters are not supported")

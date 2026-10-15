from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class CompanyConfig:
    """Company storage. Omit db to use the AgentOS PostgreSQL database.

    The service borrows its engine but owns the ``agno_company`` schema. Apply
    migrations explicitly before serving; constructing this config never connects.
    """

    db: Optional[Any] = None

    def __post_init__(self) -> None:
        if self.db is None:
            return
        from agno.db.postgres import PostgresDb

        if not isinstance(self.db, PostgresDb) or self.db.db_engine.dialect.name != "postgresql":
            raise ValueError("CompanyConfig requires a synchronous PostgresDb; other adapters are not supported")

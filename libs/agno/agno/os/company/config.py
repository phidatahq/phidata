from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class CompanyConfig:
    """Explicit Company database. PostgreSQL is the supported adapter.

    The service borrows its engine but owns the ``agno_company`` schema. Apply
    migrations explicitly before serving; constructing this config never connects.
    """

    db: Any
    # Optional read-only GitHub credential for private pull requests and API rate limits.
    github_token: Optional[str] = field(default=None, repr=False)
    # Configure a model to enable the built-in Product Manager. Omit for manual use.
    model: Optional[Any] = None

    def __post_init__(self) -> None:
        from agno.db.postgres import PostgresDb

        if not isinstance(self.db, PostgresDb) or self.db.db_engine.dialect.name != "postgresql":
            raise ValueError("CompanyConfig requires a synchronous PostgresDb; other adapters are not supported")

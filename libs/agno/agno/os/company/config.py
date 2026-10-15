"""Opt-in Company configuration and assembly-time database resolution."""

from dataclasses import dataclass
from typing import Optional, Union

from agno.db.base import AsyncBaseDb, BaseDb
from agno.models.base import Model


@dataclass
class CompanyConfig:
    db: Optional[Union[BaseDb, AsyncBaseDb]] = None
    model: Optional[Model] = None

    def resolve_db(self, default: Optional[Union[BaseDb, AsyncBaseDb]]) -> Union[BaseDb, AsyncBaseDb]:
        """Resolve and validate storage without creating tables or connecting."""
        db = self.db if self.db is not None else default
        if db is None:
            raise ValueError("Company requires CompanyConfig.db or AgentOS.db")
        if not isinstance(db, (BaseDb, AsyncBaseDb)):
            raise TypeError("Company database must implement BaseDb or AsyncBaseDb")
        base = AsyncBaseDb if isinstance(db, AsyncBaseDb) else BaseDb
        for method in (
            "create_product",
            "get_product",
            "list_products",
            "update_product",
            "upsert_member",
            "delete_member",
            "list_members",
            "get_member",
        ):
            if getattr(type(db), method, None) is getattr(base, method):
                raise ValueError(f"Company is not supported by {type(db).__name__}: {method} is not implemented")
        return db

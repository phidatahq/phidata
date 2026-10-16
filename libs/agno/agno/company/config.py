"""Opt-in Company configuration."""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

from agno.company.declarations import Product
from agno.db.base import AsyncBaseDb, BaseDb
from agno.models.base import Model


@dataclass
class CompanyConfig:
    """Company resources. An omitted database inherits AgentOS.db at assembly."""

    db: Optional[Union[BaseDb, AsyncBaseDb]] = None
    model: Optional[Model] = None
    products: List["Product"] = field(default_factory=list)
    acceptance_checks: Dict[str, Callable[[Dict[str, Any], Any], Any]] = field(default_factory=dict)
    automation_history_retention_days: int = 30

    def __post_init__(self) -> None:
        if (
            isinstance(self.automation_history_retention_days, bool)
            or not isinstance(self.automation_history_retention_days, int)
            or self.automation_history_retention_days < 1
        ):
            raise ValueError("automation_history_retention_days must be a positive integer")

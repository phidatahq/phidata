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
    max_patch_bytes: int = 2 * 1024 * 1024
    products: List["Product"] = field(default_factory=list)
    acceptance_checks: Dict[str, Callable[[Dict[str, Any], Any], Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if type(self.max_patch_bytes) is not int or self.max_patch_bytes < 1:
            raise ValueError("max_patch_bytes must be a positive integer")

"""Opt-in Company configuration."""

from dataclasses import dataclass
from typing import Optional, Union

from agno.db.base import AsyncBaseDb, BaseDb
from agno.models.base import Model


@dataclass
class CompanyConfig:
    """Company resources. An omitted database inherits AgentOS.db at assembly.

    The optional model is retained for future Product Manager support; Products
    do not require or invoke a model.
    """

    db: Optional[Union[BaseDb, AsyncBaseDb]] = None
    model: Optional[Model] = None

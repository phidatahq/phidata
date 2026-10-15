from dataclasses import dataclass
from typing import Optional, Union

from agno.db.base import AsyncBaseDb, BaseDb


@dataclass(frozen=True)
class CompanyConfig:
    """Enable Company; an explicit database overrides the AgentOS database.

    Synchronous PostgresDb and SqliteDb are supported. Schema initialization is an
    explicit deployment step on ``agent_os.company.initialize_schema()``.
    """

    db: Optional[Union[BaseDb, AsyncBaseDb]] = None

"""Configuration for OS Manager."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from agno.offload import ResultStore

from agno.registry._reserved import BUILDER_ID as BUILDER_ID
from agno.registry._reserved import MANAGER_TEAM_ID, RESERVED_MANAGER_IDS
from agno.registry._reserved import OPERATOR_ID as OPERATOR_ID

MANAGER_TEAM_NAME = "OS Manager"
RESERVED_MEMBER_IDS = RESERVED_MANAGER_IDS - {MANAGER_TEAM_ID}


@dataclass
class OSManager:
    """Configure the OS manager and its resources.

    When authorization is enforced, ordinary component run grants allow access.
    Protected tools check the caller's permissions during manager execution
    and delegated work. Ordinary agents retain their existing tool permissions.
    Direct Python calls and bound interfaces are trusted application entry points.

    Args:
        name: The manager team's display name.
        model: Model for the manager and its members. Uses the registry's first
            model if omitted. A model is required in one of these places.
        tools: Extra tools for the manager team, such as charts or notebooks.
            These are not added to its members or to the registry.
        knowledge: Knowledge base the manager can search.
        learning: Learning machine for remembering users across sessions.
        root: Directory or WorkspaceContextProvider for Platform Manager to read.
            Default file exclusions apply. Extra exclusions are allowed; custom
            exemptions and allow_paths are not. Omit to disable source access.
        access_docs: Give Platform Manager access to the Agno documentation MCP
            server. Enabled by default. Connection failures are nonfatal; pass
            False to disable documentation access in offline deployments.
        offload_tool_results: Offload large tool results for the manager and its members.
            Enabled by default on SQLite and PostgreSQL. Pass False to disable or
            a ResultStore to customize its settings.
        instructions: Extra instructions for the manager.
        required_env: Environment variables to check during diagnostics.
        num_history_runs: Number of past runs to include in the manager's context.
    """

    name: str = MANAGER_TEAM_NAME
    model: Optional[Any] = None
    tools: List[Any] = field(default_factory=list)
    knowledge: Optional[Any] = None
    learning: Optional[Any] = None
    root: Optional[Union[str, Path, Any]] = None
    access_docs: bool = True
    offload_tool_results: Optional[Union[bool, "ResultStore"]] = True
    instructions: Optional[str] = None
    required_env: Tuple[str, ...] = ()
    num_history_runs: int = 7

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("OSManager.name must not be empty")
        if self.num_history_runs < 0:
            raise ValueError("OSManager.num_history_runs must not be negative")

    @property
    def id(self) -> str:
        """The fixed, reserved id of the served manager team."""
        return MANAGER_TEAM_ID

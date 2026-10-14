"""Configuration for OS Manager."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from agno.offload import ResultStore

MANAGER_TEAM_ID = "os-manager"
MANAGER_TEAM_NAME = "OS Manager"
BUILDER_ID = "platform-builder"
OPERATOR_ID = "platform-manager"
ENGINEER_ID = "platform-engineer"
# Member ids are fixed. Set the team id to reuse an existing team's sessions.
RESERVED_MEMBER_IDS = frozenset({BUILDER_ID, OPERATOR_ID, ENGINEER_ID})


@dataclass
class ManagerConfig:
    """Configure the OS manager and its resources.

    When authorization is enforced, ordinary component run grants allow access.
    Built-in tools check the caller's permissions for each operation.
    Direct Python calls and bound interfaces are trusted application entry points.

    Args:
        name: The manager team's display name.
        model: Model for the manager and its members. Uses the registry's first
            model if omitted. A model is required in one of these places.
        id: The manager team's id. Member ids are fixed.
        tools: Tools for the manager. These are not added to the registry.
        knowledge: Knowledge base the manager can search.
        learning: Learning machine for remembering users across sessions.
        workspace: Directory or WorkspaceContextProvider for Platform Engineer to
            read. Default file exclusions apply. Extra exclusions are allowed;
            custom exemptions and allow_paths are not. Omit to disable the engineer.
        offload_tool_results: Offload large tool results for the manager and its members.
            Enabled by default on SQLite and PostgreSQL. Pass False to disable or
            a ResultStore to customize its settings.
        instructions: Extra instructions for the manager.
        required_env: Environment variables to check during diagnostics.
        num_history_runs: Number of past runs to include in the manager's context.
    """

    name: str = MANAGER_TEAM_NAME
    model: Optional[Any] = None
    id: str = MANAGER_TEAM_ID
    tools: List[Any] = field(default_factory=list)
    knowledge: Optional[Any] = None
    learning: Optional[Any] = None
    workspace: Optional[Union[str, Path, Any]] = None
    offload_tool_results: Optional[Union[bool, "ResultStore"]] = True
    instructions: Optional[str] = None
    required_env: Tuple[str, ...] = ()
    num_history_runs: int = 7

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("ManagerConfig.name must not be empty")
        if not self.id or not self.id.strip():
            raise ValueError("ManagerConfig.id must not be empty")
        if self.id in RESERVED_MEMBER_IDS:
            raise ValueError(f"ManagerConfig.id {self.id!r} is reserved for a manager member")
        if self.num_history_runs < 0:
            raise ValueError("ManagerConfig.num_history_runs must not be negative")

from enum import Enum


class WorkspaceStarterTemplate(str, Enum):
    agent_app_ecs = "agent-app-ecs"
    agent_api_ecs = "agent-api-ecs"

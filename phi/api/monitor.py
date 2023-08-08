from typing import Optional, Union, Dict, List

from httpx import Response

from phi.api.api import api, invalid_response
from phi.api.routes import ApiRoutes
from phi.api.schemas.monitor import MonitorEventSchema, MonitorResponseSchema
from phi.api.schemas.workspace import WorkspaceSchema
from phi.cli.settings import phi_cli_settings
from phi.utils.log import logger


def log_monitor_event(monitor: MonitorEventSchema, workspace: WorkspaceSchema) -> Optional[MonitorResponseSchema]:
    if not phi_cli_settings.api_enabled:
        return None

    logger.debug("--o-o-- Log monitor event")
    with api.Client() as api_client:
        try:
            r: Response = api_client.post(
                ApiRoutes.MONITOR_EVENT_CREATE,
                json={
                    "monitor": monitor.model_dump(exclude_none=True),
                    "workspace": workspace.model_dump(include={"id_workspace"}),
                },
            )
            if invalid_response(r):
                return None

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return None

            monitor_response: MonitorResponseSchema = MonitorResponseSchema.model_validate(response_json)
            if monitor_response is not None:
                return monitor_response
        except Exception as e:
            logger.debug(f"Could not log monitor event: {e}")
    return None

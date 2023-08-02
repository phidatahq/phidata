from typing import Optional

from phi.api.client import api_client, invalid_response
from phi.api.routes import ApiRoutes
from phi.api.schemas.monitor import MonitorEventSchema, MonitorResponseSchema
from phi.api.schemas.workspace import WorkspaceSchema
from phi.cli.settings import phi_cli_settings
from phi.utils.log import logger


async def log_monitor_event(monitor: MonitorEventSchema, workspace: WorkspaceSchema) -> Optional[MonitorResponseSchema]:
    if not phi_cli_settings.api_enabled:
        return None

    logger.debug("--o-o-- Log monitor event")
    try:
        async with api_client.Session() as api:
            async with api.post(
                ApiRoutes.MONITOR_EVENT,
                json={
                    "monitor": monitor.model_dump(exclude_none=True),
                    "workspace": workspace.model_dump(include={"id_workspace"}),
                },
            ) as response:
                if invalid_response(response):
                    return None

                response_json = await response.json()
                if response_json is None:
                    return None

                # logger.info(response_json)
                try:
                    monitor_response: MonitorResponseSchema = MonitorResponseSchema.model_validate(response_json)
                    if monitor_response is not None:
                        return monitor_response
                    return None
                except Exception as e:
                    logger.warning(e)
    except Exception as e:
        logger.debug(f"Could not log monitor event: {e}")
    return None

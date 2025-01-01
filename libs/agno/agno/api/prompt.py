from os import getenv
from typing import Union, Dict, List, Optional, Tuple

from httpx import Response

from phi.api.api import api, invalid_response
from phi.api.routes import ApiRoutes
from phi.api.schemas.prompt import (
    PromptRegistrySync,
    PromptTemplatesSync,
    PromptRegistrySchema,
    PromptTemplateSync,
    PromptTemplateSchema,
)
from phi.api.schemas.workspace import WorkspaceIdentifier
from phi.constants import WORKSPACE_ID_ENV_VAR, WORKSPACE_KEY_ENV_VAR
from phi.cli.settings import phi_cli_settings
from phi.utils.common import str_to_int
from phi.utils.log import logger


def sync_prompt_registry_api(
    registry: PromptRegistrySync, templates: PromptTemplatesSync
) -> Tuple[Optional[PromptRegistrySchema], Optional[Dict[str, PromptTemplateSchema]]]:
    if not phi_cli_settings.api_enabled:
        return None, None

    logger.debug("--o-o-- Syncing Prompt Registry --o-o--")
    with api.AuthenticatedClient() as api_client:
        try:
            workspace_identifier = WorkspaceIdentifier(
                id_workspace=str_to_int(getenv(WORKSPACE_ID_ENV_VAR)),
                ws_key=getenv(WORKSPACE_KEY_ENV_VAR),
            )
            r: Response = api_client.post(
                ApiRoutes.PROMPT_REGISTRY_SYNC,
                json={
                    "registry": registry.model_dump(exclude_none=True),
                    "templates": templates.model_dump(exclude_none=True),
                    "workspace": workspace_identifier.model_dump(exclude_none=True),
                },
            )
            if invalid_response(r):
                return None, None

            response_dict: Dict = r.json()
            if response_dict is None:
                return None, None

            # logger.debug(f"Response: {response_dict}")
            registry_response: PromptRegistrySchema = PromptRegistrySchema.model_validate(
                response_dict.get("registry", {})
            )
            templates_response: Dict[str, PromptTemplateSchema] = {
                k: PromptTemplateSchema.model_validate(v) for k, v in response_dict.get("templates", {}).items()
            }
            return registry_response, templates_response
        except Exception as e:
            logger.debug(f"Could not sync prompt registry: {e}")
    return None, None


def sync_prompt_template_api(
    registry: PromptRegistrySync, prompt_template: PromptTemplateSync
) -> Optional[PromptTemplateSchema]:
    if not phi_cli_settings.api_enabled:
        return None

    logger.debug("--o-o-- Syncing Prompt Template --o-o--")
    with api.AuthenticatedClient() as api_client:
        try:
            workspace_identifier = WorkspaceIdentifier(
                id_workspace=str_to_int(getenv(WORKSPACE_ID_ENV_VAR)),
                ws_key=getenv(WORKSPACE_KEY_ENV_VAR),
            )
            r: Response = api_client.post(
                ApiRoutes.PROMPT_TEMPLATE_SYNC,
                json={
                    "registry": registry.model_dump(exclude_none=True),
                    "template": prompt_template.model_dump(exclude_none=True),
                    "workspace": workspace_identifier.model_dump(exclude_none=True),
                },
            )
            if invalid_response(r):
                return None

            response_dict: Union[Dict, List] = r.json()
            if response_dict is None:
                return None

            # logger.debug(f"Response: {response_dict}")
            return PromptTemplateSchema.model_validate(response_dict)
        except Exception as e:
            logger.debug(f"Could not sync prompt template: {e}")
    return None

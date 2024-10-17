from typing import List, Optional

from pydantic import field_validator, Field
from pydantic_settings import BaseSettings
from pydantic_core.core_schema import FieldValidationInfo


class ApiSettings(BaseSettings):
    """Api settings that can be set using environment variables.

    Reference: https://pydantic-docs.helpmanual.io/usage/settings/
    """

    # Api title and version
    title: str = "agent-app"
    version: str = "1.0"

    # Api runtime_env derived from the `runtime_env` environment variable.
    # Valid values include "dev", "stg", "prd"
    runtime_env: str = "dev"

    # Set to False to disable docs at /docs and /redoc
    docs_enabled: bool = True

    # Cors origin list to allow requests from.
    # This list is set using the set_cors_origin_list validator
    # which uses the runtime_env variable to set the
    # default cors origin list.
    cors_origin_list: Optional[List[str]] = Field(None, validate_default=True)

    @field_validator("runtime_env")
    def validate_runtime_env(cls, runtime_env):
        """Validate runtime_env."""

        valid_runtime_envs = ["dev", "stg", "prd"]
        if runtime_env not in valid_runtime_envs:
            raise ValueError(f"Invalid runtime_env: {runtime_env}")

        return runtime_env

    @field_validator("cors_origin_list", mode="before")
    def set_cors_origin_list(cls, cors_origin_list, info: FieldValidationInfo):
        valid_cors = cors_origin_list or []

        # Add phidata.app to cors origin list
        valid_cors.extend(["https://phidata.app", "https://www.phidata.app"])

        runtime_env = info.data.get("runtime_env")
        if runtime_env == "dev":
            # 3000 is the default port for create-react-app
            valid_cors.extend(["http://localhost", "http://localhost:3000"])

        return valid_cors


# Create ApiSettings object
api_settings = ApiSettings()

from pathlib import Path
from importlib import metadata

from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_core.core_schema import FieldValidationInfo

PHI_CLI_DIR: Path = Path.home().resolve().joinpath(".phi")


class PhiCliSettings(BaseSettings):
    app_name: str = "phi"
    app_version: str = metadata.version("phidata")

    tmp_token_path: Path = PHI_CLI_DIR.joinpath("tmp_token")
    config_file_path: Path = PHI_CLI_DIR.joinpath("config.json")
    credentials_path: Path = PHI_CLI_DIR.joinpath("credentials.json")
    ai_conversations_path: Path = PHI_CLI_DIR.joinpath("ai_conversations.json")
    auth_token_cookie: str = "__phi_session"
    auth_token_header: str = "X-PHIDATA-AUTH-TOKEN"

    api_runtime: str = "prd"
    api_enabled: bool = True
    api_url: str = Field("https://api.phidata.com", validate_default=True)
    signin_url: str = Field("https://phidata.app/login", validate_default=True)

    model_config = SettingsConfigDict(env_prefix="PHI_")

    @field_validator("api_runtime", mode="before")
    def validate_runtime_env(cls, v):
        """Validate api_runtime."""

        valid_api_runtimes = ["dev", "stg", "prd"]
        if v not in valid_api_runtimes:
            raise ValueError(f"Invalid api_runtime: {v}")

        return v

    @field_validator("signin_url", mode="before")
    def update_signin_url(cls, v, info: FieldValidationInfo):
        api_runtime = info.data["api_runtime"]
        if api_runtime == "dev":
            return "http://localhost:3000/login"
        elif api_runtime == "stg":
            return "https://stgphi.com/login"
        else:
            return "https://phidata.app/login"

    @field_validator("api_url", mode="before")
    def update_api_url(cls, v, info: FieldValidationInfo):
        api_runtime = info.data["api_runtime"]
        if api_runtime == "dev":
            from os import getenv

            if getenv("PHI_RUNTIME") == "docker":
                return "http://host.docker.internal:7070"
            return "http://localhost:7070"
        elif api_runtime == "stg":
            return "https://api.stgphi.com"
        else:
            return "https://api.phidata.com"


phi_cli_settings = PhiCliSettings()

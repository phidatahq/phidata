from pathlib import Path
from importlib import metadata

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_core.core_schema import FieldValidationInfo

from phi.utils.log import logger

PHI_CLI_DIR: Path = Path.home().resolve().joinpath(".phi")


class PhiCliSettings(BaseSettings):
    app_name: str = "phi"
    app_version: str = metadata.version("phi")

    config_file_path: Path = PHI_CLI_DIR.joinpath("config")
    auth_token_path: Path = PHI_CLI_DIR.joinpath("token")
    credentials_path: Path = PHI_CLI_DIR.joinpath("credentials")

    runtime: str = "prd"
    auth_token_cookie: str = "__phi_session"
    auth_token_header: str = "X-PHIDATA-AUTH-TOKEN"
    signin_url: str = "https://phidata.com/signin"
    api_url: str = "https://api.phidata.com"

    model_config = SettingsConfigDict(env_prefix="PHI_CLI_")

    @field_validator("signin_url", mode="before")
    def update_signin_url(cls, v, info: FieldValidationInfo):
        logger.info(f"Validating {v} | info: {info}")
        if "runtime" in info.data:
            if info.data["runtime"] == "dev":
                return "http://localhost:3000/signin"

        return v

    @field_validator("api_url", mode="before")
    def update_api_url(cls, v, info: FieldValidationInfo):
        logger.info(f"Validating {v} | info: {info}")
        if "runtime" in info.data:
            if info.data["runtime"] == "dev":
                return "http://localhost:8000"

        return v


phi_cli_settings = PhiCliSettings()

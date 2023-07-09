from pathlib import Path
from importlib import metadata

from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_core.core_schema import FieldValidationInfo

PHI_CLI_DIR: Path = Path.home().resolve().joinpath(".phi")


class PhiCliSettings(BaseSettings):
    app_name: str = "phi"
    app_version: str = metadata.version("phidata")

    config_file_path: Path = PHI_CLI_DIR.joinpath("config")
    auth_token_path: Path = PHI_CLI_DIR.joinpath("token")
    credentials_path: Path = PHI_CLI_DIR.joinpath("credentials")

    # These fields are used to update the final signin_url and api_url values
    # Not to be used directly
    dev_signin_url: str = "http://localhost:3000/signin"
    dev_api_url: str = "http://localhost:8000"
    prd_signin_url: str = "https://phidata.com/signin"
    prd_api_url: str = "https://api.phidata.com"

    runtime: str = "prd"
    auth_token_cookie: str = "__phi_session"
    auth_token_header: str = "X-PHIDATA-AUTH-TOKEN"
    signin_url: str = Field("https://phidata.com/signin", validate_default=True)
    api_url: str = Field("https://api.phidata.com", validate_default=True)

    model_config = SettingsConfigDict(env_prefix="PHI_CLI_")

    @field_validator("signin_url", mode="before")
    def update_signin_url(cls, v, info: FieldValidationInfo):
        dev_signin_url = info.data.get("dev_signin_url", "http://localhost:3000/signin")
        prd_signin_url = info.data.get("prd_signin_url", "https://phidata.com/signin")
        signin_url = dev_signin_url if info.data["runtime"] == "dev" else prd_signin_url
        return signin_url

    @field_validator("api_url", mode="before")
    def update_api_url(cls, v, info: FieldValidationInfo):
        dev_api_url = info.data.get("dev_api_url", "http://localhost:8000")
        prd_api_url = info.data.get("prd_api_url", "https://api.phidata.com")
        api_url = dev_api_url if info.data["runtime"] == "dev" else prd_api_url
        return api_url


phi_cli_settings = PhiCliSettings()

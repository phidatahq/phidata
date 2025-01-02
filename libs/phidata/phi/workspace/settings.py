from __future__ import annotations

from pathlib import Path
from typing import Optional, List, Dict

from pydantic import field_validator, ValidationInfo, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from phi.api.schemas.workspace import WorkspaceSchema


class WorkspaceSettings(BaseSettings):
    """
    -*- Workspace settings
    Initialize workspace settings by:
    1. Creating a WorkspaceSettings object
    2. Using Environment variables
    3. Using the .env file
    """

    # Workspace name: used for naming cloud resources
    ws_name: str
    # Path to the workspace root
    ws_root: Path
    # Workspace git repo url: used to git-sync DAGs and Charts
    ws_repo: Optional[str] = None
    # Path to important directories relative to the ws_root
    scripts_dir: str = "scripts"
    storage_dir: str = "storage"
    workflows_dir: str = "workflows"
    workspace_dir: str = "workspace"
    # default env for phi ws commands
    default_env: Optional[str] = "dev"
    # default infra for phi ws commands
    default_infra: Optional[str] = None
    #
    # -*- Image Settings
    #
    # Repository for images
    image_repo: str = "phidata"
    # Name:tag for the image
    image_name: Optional[str] = None
    # Build images locally
    build_images: bool = False
    # Push images after building
    push_images: bool = False
    # Skip cache when building images
    skip_image_cache: bool = False
    # Force pull images in FROM
    force_pull_images: bool = False
    #
    # -*- Dev settings
    #
    dev_env: str = "dev"
    # Dev git repo branch: used to git-sync DAGs and Charts
    dev_branch: str = "main"
    # Key for naming dev resources
    dev_key: Optional[str] = None
    # Tags for dev resources
    dev_tags: Optional[Dict[str, str]] = None
    # Domain for the dev platform
    dev_domain: Optional[str] = None
    #
    # -*- Dev Apps
    #
    dev_api_enabled: bool = False
    dev_app_enabled: bool = False
    dev_db_enabled: bool = False
    dev_redis_enabled: bool = False
    #
    # -*- Staging settings
    #
    stg_env: str = "stg"
    # Staging git repo branch: used to git-sync DAGs and Charts
    stg_branch: str = "main"
    # Key for naming staging resources
    stg_key: Optional[str] = None
    # Tags for staging resources
    stg_tags: Optional[Dict[str, str]] = None
    # Domain for the staging platform
    stg_domain: Optional[str] = None
    #
    # -*- Staging Apps
    #
    stg_api_enabled: bool = False
    stg_app_enabled: bool = False
    stg_db_enabled: bool = False
    stg_redis_enabled: bool = False
    #
    # -*- Production settings
    #
    prd_env: str = "prd"
    # Production git repo branch: used to git-sync DAGs and Charts
    prd_branch: str = "main"
    # Key for naming production resources
    prd_key: Optional[str] = None
    # Tags for production resources
    prd_tags: Optional[Dict[str, str]] = None
    # Domain for the production platform
    prd_domain: Optional[str] = None
    #
    # -*- Production Apps
    #
    prd_api_enabled: bool = False
    prd_app_enabled: bool = False
    prd_db_enabled: bool = False
    prd_redis_enabled: bool = False
    #
    # -*- AWS settings
    #
    # Region for AWS resources
    aws_region: Optional[str] = None
    # Availability Zones for AWS resources
    aws_az1: Optional[str] = None
    aws_az2: Optional[str] = None
    aws_az3: Optional[str] = None
    aws_az4: Optional[str] = None
    aws_az5: Optional[str] = None
    # Public subnets. 1 in each AZ.
    public_subnets: List[str] = Field(default_factory=list)
    # Private subnets. 1 in each AZ.
    private_subnets: List[str] = Field(default_factory=list)
    # Subnet IDs. 1 in each AZ.
    # Derived from public and private subnets if not provided.
    subnet_ids: Optional[List[str]] = None
    # Security Groups
    security_groups: Optional[List[str]] = None
    aws_profile: Optional[str] = None
    aws_config_file: Optional[str] = None
    aws_shared_credentials_file: Optional[str] = None
    # -*- Cli settings
    # Set to True if `phi` should continue creating
    # resources after a resource creation has failed
    continue_on_create_failure: bool = False
    # Set to True if `phi` should continue deleting
    # resources after a resource deleting has failed
    # Defaults to True because we normally want to continue deleting
    continue_on_delete_failure: bool = True
    # Set to True if `phi` should continue patching
    # resources after a resource patch has failed
    continue_on_patch_failure: bool = False
    #
    # -*- Other Settings
    #
    use_cache: bool = True
    # WorkspaceSchema provided by the api
    ws_schema: Optional[WorkspaceSchema] = None

    model_config = SettingsConfigDict(extra="allow")

    @field_validator("dev_key", mode="before")
    def set_dev_key(cls, dev_key, info: ValidationInfo):
        if dev_key is not None:
            return dev_key

        ws_name = info.data.get("ws_name")
        if ws_name is None:
            raise ValueError("ws_name invalid")

        dev_env = info.data.get("dev_env")
        if dev_env is None:
            raise ValueError("dev_env invalid")

        return f"{dev_env}-{ws_name}"

    @field_validator("dev_tags", mode="before")
    def set_dev_tags(cls, dev_tags, info: ValidationInfo):
        if dev_tags is not None:
            return dev_tags

        ws_name = info.data.get("ws_name")
        if ws_name is None:
            raise ValueError("ws_name invalid")

        dev_env = info.data.get("dev_env")
        if dev_env is None:
            raise ValueError("dev_env invalid")

        return {
            "Env": dev_env,
            "Project": ws_name,
        }

    @field_validator("stg_key", mode="before")
    def set_stg_key(cls, stg_key, info: ValidationInfo):
        if stg_key is not None:
            return stg_key

        ws_name = info.data.get("ws_name")
        if ws_name is None:
            raise ValueError("ws_name invalid")

        stg_env = info.data.get("stg_env")
        if stg_env is None:
            raise ValueError("stg_env invalid")

        return f"{stg_env}-{ws_name}"

    @field_validator("stg_tags", mode="before")
    def set_stg_tags(cls, stg_tags, info: ValidationInfo):
        if stg_tags is not None:
            return stg_tags

        ws_name = info.data.get("ws_name")
        if ws_name is None:
            raise ValueError("ws_name invalid")

        stg_env = info.data.get("stg_env")
        if stg_env is None:
            raise ValueError("stg_env invalid")

        return {
            "Env": stg_env,
            "Project": ws_name,
        }

    @field_validator("prd_key", mode="before")
    def set_prd_key(cls, prd_key, info: ValidationInfo):
        if prd_key is not None:
            return prd_key

        ws_name = info.data.get("ws_name")
        if ws_name is None:
            raise ValueError("ws_name invalid")

        prd_env = info.data.get("prd_env")
        if prd_env is None:
            raise ValueError("prd_env invalid")

        return f"{prd_env}-{ws_name}"

    @field_validator("prd_tags", mode="before")
    def set_prd_tags(cls, prd_tags, info: ValidationInfo):
        if prd_tags is not None:
            return prd_tags

        ws_name = info.data.get("ws_name")
        if ws_name is None:
            raise ValueError("ws_name invalid")

        prd_env = info.data.get("prd_env")
        if prd_env is None:
            raise ValueError("prd_env invalid")

        return {
            "Env": prd_env,
            "Project": ws_name,
        }

    @field_validator("subnet_ids", mode="before")
    def set_subnet_ids(cls, subnet_ids, info: ValidationInfo):
        if subnet_ids is not None:
            return subnet_ids

        public_subnets = info.data.get("public_subnets", [])
        private_subnets = info.data.get("private_subnets", [])

        return public_subnets + private_subnets

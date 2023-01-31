from pathlib import Path
from typing import Optional, List, Dict

from pydantic import BaseSettings, validator, Extra


class WorkspaceSettings(BaseSettings, extra=Extra.allow):
    """
    -*- Workspace settings
    Initialize workspace settings by:
    1. Creating a WorkspaceSettings object
    2. Using Environment variables
    3. Using the .env file
    """

    # Workspace name: used for naming cloud resources
    ws_name: str
    # Workspace git repo url: used to git-sync DAGs and Charts
    ws_repo: Optional[str] = None
    # Path to the workspace directory
    ws_dir: Path
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
    dev_airbyte_enabled: bool = False
    dev_airflow_enabled: bool = False
    dev_api_enabled: bool = False
    dev_assistant_enabled: bool = False
    dev_databox_enabled: bool = False
    dev_jupyter_enabled: bool = False
    dev_postgres_enabled: bool = False
    dev_redis_enabled: bool = False
    dev_superset_enabled: bool = False
    dev_traefik_enabled: bool = False
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
    stg_airbyte_enabled: bool = False
    stg_airflow_enabled: bool = False
    stg_api_enabled: bool = False
    stg_assistant_enabled: bool = False
    stg_databox_enabled: bool = False
    stg_jupyter_enabled: bool = False
    stg_postgres_enabled: bool = False
    stg_redis_enabled: bool = False
    stg_superset_enabled: bool = False
    stg_traefik_enabled: bool = False
    stg_whoami_enabled: bool = False
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
    prd_airbyte_enabled: bool = False
    prd_airflow_enabled: bool = False
    prd_api_enabled: bool = False
    prd_assistant_enabled: bool = False
    prd_databox_enabled: bool = False
    prd_jupyter_enabled: bool = False
    prd_postgres_enabled: bool = False
    prd_redis_enabled: bool = False
    prd_superset_enabled: bool = False
    prd_traefik_enabled: bool = False
    prd_whoami_enabled: bool = False
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
    public_subnets: List[str] = []
    # Private subnets. 1 in each AZ.
    private_subnets: List[str] = []
    # Subnet IDs. 1 in each AZ.
    # Derived from public and private subnets if not provided.
    subnet_ids: Optional[List[str]] = None
    # Security Groups
    security_groups: Optional[List[str]] = None
    #
    # -*- Image Settings
    #
    # Repository for images
    image_repo: str = "phidata"
    # Suffix added to the image name
    image_suffix: str = "aws-dp"
    # Build images locally
    build_images: bool = False
    # Push images after building
    push_images: bool = False
    # Skip cache when building images
    skip_image_cache: bool = False
    # Force pull images in FROM
    force_pull_images: bool = False
    #
    # -*- Other Settings
    #
    use_cache: bool = True

    @validator("dev_key", always=True)
    def set_dev_key(cls, dev_key, values):
        if dev_key is not None:
            return dev_key

        ws_name = values.get("ws_name")
        if ws_name is None:
            raise ValueError("ws_name invalid")

        dev_env = values.get("dev_env")
        if dev_env is None:
            raise ValueError("dev_env invalid")

        return f"{ws_name}-{dev_env}"

    @validator("dev_tags", always=True)
    def set_dev_tags(cls, dev_tags, values):
        if dev_tags is not None:
            return dev_tags

        ws_name = values.get("ws_name")
        if ws_name is None:
            raise ValueError("ws_name invalid")

        dev_env = values.get("dev_env")
        if dev_env is None:
            raise ValueError("dev_env invalid")

        return {
            "Env": dev_env,
            "Project": ws_name,
        }

    @validator("stg_key", always=True)
    def set_stg_key(cls, stg_key, values):
        if stg_key is not None:
            return stg_key

        ws_name = values.get("ws_name")
        if ws_name is None:
            raise ValueError("ws_name invalid")

        stg_env = values.get("stg_env")
        if stg_env is None:
            raise ValueError("stg_env invalid")

        return f"{ws_name}-{stg_env}"

    @validator("stg_tags", always=True)
    def set_stg_tags(cls, stg_tags, values):
        if stg_tags is not None:
            return stg_tags

        ws_name = values.get("ws_name")
        if ws_name is None:
            raise ValueError("ws_name invalid")

        stg_env = values.get("stg_env")
        if stg_env is None:
            raise ValueError("stg_env invalid")

        return {
            "Env": stg_env,
            "Project": ws_name,
        }

    @validator("prd_key", always=True)
    def set_prd_key(cls, prd_key, values):
        if prd_key is not None:
            return prd_key

        ws_name = values.get("ws_name")
        if ws_name is None:
            raise ValueError("ws_name invalid")

        prd_env = values.get("prd_env")
        if prd_env is None:
            raise ValueError("prd_env invalid")

        return f"{ws_name}-{prd_env}"

    @validator("prd_tags", always=True)
    def set_prd_tags(cls, prd_tags, values):
        if prd_tags is not None:
            return prd_tags

        ws_name = values.get("ws_name")
        if ws_name is None:
            raise ValueError("ws_name invalid")

        prd_env = values.get("prd_env")
        if prd_env is None:
            raise ValueError("prd_env invalid")

        return {
            "Env": prd_env,
            "Project": ws_name,
        }

    @validator("subnet_ids", always=True)
    def set_subnet_ids(cls, subnet_ids, values):
        if subnet_ids is not None:
            return subnet_ids

        public_subnets = values.get("public_subnets")
        private_subnets = values.get("private_subnets")

        return public_subnets + private_subnets

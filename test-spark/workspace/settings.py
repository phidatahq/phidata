from pathlib import Path

from phidata.workspace.settings import WorkspaceSettings

#
# -*- Define workspace settings using the WorkspaceSettings class
#
ws_settings = WorkspaceSettings(
    # Workspace name: used for naming cloud resources
    ws_name="dp003",
    # Workspace git repo url: used to git-sync DAGs and Charts
    ws_repo="https://github.com/phidatahq/aws-spark-dp-template.git",
    # Path to the workspace root
    ws_root=Path(__file__).parent.parent.resolve(),
    # -*- Dev settings
    dev_env="dev",
    # -*- Dev Apps
    dev_jupyter_enabled=True,
    # dev_airflow_enabled=True,
    # dev_postgres_enabled=True,
    # dev_spark_enabled=True,
    # dev_superset_enabled=True,
    # dev_traefik_enabled=True,
    # dev_databox_enabled=True,
    # dev_assistant_enabled=True,
    # -*- Production settings
    prd_env="prd",
    # Production branch: used for git-sync
    # prd_branch: str = "main",
    # Domain for the production platform
    prd_domain="dp003.xyz",
    # -*- Production Apps
    prd_airflow_enabled=True,
    prd_jupyter_enabled=True,
    prd_spark_enabled=True,
    prd_superset_enabled=True,
    prd_traefik_enabled=True,
    prd_whoami_enabled=True,
    # prd_postgres_enabled=True,
    # prd_databox_enabled=True,
    # prd_assistant_enabled=True,
    # -*- AWS settings
    # Region for AWS resources
    aws_region="us-east-1",
    # Availability Zones for AWS resources
    aws_az1="us-east-1a",
    aws_az2="us-east-1b",
    # Subnet IDs for AWS resources
    subnet_ids=None,
    # Security Groups for AWS resources
    security_groups=None,
    # -*- Image Settings
    # Repository for images
    # image_repo="your-repo",
    # Suffix added to the image name
    image_suffix="aws-spark-dp",
    # Build images locally
    # build_images=True,
    # Push images after building
    # push_images=True,
    # Skip cache when building images
    # skip_image_cache=False,
    # Force pull images in FROM
    # force_pull_images=False,
)

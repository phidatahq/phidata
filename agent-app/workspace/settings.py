from pathlib import Path

from phi.workspace.settings import WorkspaceSettings

#
# -*- Define workspace settings using a WorkspaceSettings object
# these values can also be set using environment variables or a .env file
#
ws_settings = WorkspaceSettings(
    # Workspace name: used for naming cloud resources
    ws_name="agent",
    # Path to the workspace root
    ws_root=Path(__file__).parent.parent.resolve(),
    # -*- Development env settings
    dev_env="dev",
    # -*- Development Apps
    dev_app_enabled=True,
    dev_api_enabled=True,
    dev_db_enabled=True,
    # -*- Production env settings
    prd_env="prd",
    # -*- Production Apps
    prd_app_enabled=True,
    prd_api_enabled=True,
    prd_db_enabled=True,
    # -*- AWS settings
    # Region for AWS resources
    aws_region="us-east-1",
    # Availability Zones for AWS resources
    aws_az1="us-east-1a",
    aws_az2="us-east-1b",
    # Subnet IDs in the aws_region
    subnet_ids=["subnet-0d2a120b179e668db", "subnet-047026115db0ee35b"],
    # -*- Image Settings
    # Name of the image
    image_name="agent-app",
    # Repository for the image
    # image_repo="phidata",
    # Build images locally
    # build_images=True,
)

from phidata.infra.base import InfraConfig
from phidata.workspace import WorkspaceConfig

from phidata.utils.log import logger


def prep_infra_config(
    infra_config: InfraConfig,
    ws_config: WorkspaceConfig,
) -> InfraConfig:

    logger.debug(f"Updating {infra_config.__class__.__name__} using WorkspaceConfig")

    ######################################################################
    # NOTE: VERY IMPORTANT TO GET RIGHT
    # Prep InfraConfig using the WorkspaceConfig
    # 1. Pass down the paths from the WorkspaceConfig
    #       These paths are used everywhere from Infra, Apps, Resources, Workflows
    # 2. Pass down local_env, docker_env, k8s_env
    # 3. Pass down common cloud configuration. eg: aws_region, aws_profile
    ######################################################################

    # -*- Path parameters
    infra_config.scripts_dir = ws_config.scripts_dir
    infra_config.storage_dir = ws_config.storage_dir
    infra_config.meta_dir = ws_config.meta_dir
    infra_config.products_dir = ws_config.products_dir
    infra_config.notebooks_dir = ws_config.notebooks_dir
    infra_config.workflows_dir = ws_config.workflows_dir
    # The workspace_root_path is the ROOT directory for the workspace
    infra_config.workspace_root_path = ws_config.workspace_root_path
    infra_config.workspace_config_dir = ws_config.workspace_config_dir
    infra_config.workspace_config_file_path = ws_config.workspace_config_file_path

    # -*- Environment parameters
    # only update the param if they are not available.
    # i.e. prefer the configs param if provided
    if infra_config.local_env is None and ws_config.local_env is not None:
        infra_config.local_env = ws_config.local_env
    if infra_config.local_env_file is None and ws_config.local_env_file is not None:
        infra_config.local_env_file = ws_config.local_env_file
    if infra_config.docker_env is None and ws_config.docker_env is not None:
        infra_config.docker_env = ws_config.docker_env
    if infra_config.docker_env_file is None and ws_config.docker_env_file is not None:
        infra_config.docker_env_file = ws_config.docker_env_file
    if infra_config.k8s_env is None and ws_config.k8s_env is not None:
        infra_config.k8s_env = ws_config.k8s_env
    if infra_config.k8s_env_file is None and ws_config.k8s_env_file is not None:
        infra_config.k8s_env_file = ws_config.k8s_env_file

    # -*- AWS parameters
    # only update the param if they are available.
    # i.e. prefer the configs param if provided
    if infra_config.aws_region is None and ws_config.aws_region is not None:
        infra_config.aws_region = ws_config.aws_region
    if infra_config.aws_profile is None and ws_config.aws_profile is not None:
        infra_config.aws_profile = ws_config.aws_profile
    if infra_config.aws_config_file is None and ws_config.aws_config_file is not None:
        infra_config.aws_config_file = ws_config.aws_config_file
    if (
        infra_config.aws_shared_credentials_file is None
        and ws_config.aws_shared_credentials_file is not None
    ):
        infra_config.aws_shared_credentials_file = ws_config.aws_shared_credentials_file

    # -*- `phi` cli parameters
    # only update the param if they are available.
    # i.e. prefer the configs param if provided
    if (
        infra_config.continue_on_create_failure is None
        and ws_config.continue_on_create_failure is not None
    ):
        infra_config.continue_on_create_failure = ws_config.continue_on_create_failure
    if (
        infra_config.continue_on_delete_failure is None
        and ws_config.continue_on_delete_failure is not None
    ):
        infra_config.continue_on_delete_failure = ws_config.continue_on_delete_failure
    if (
        infra_config.continue_on_patch_failure is None
        and ws_config.continue_on_patch_failure is not None
    ):
        infra_config.continue_on_patch_failure = ws_config.continue_on_patch_failure

    return infra_config

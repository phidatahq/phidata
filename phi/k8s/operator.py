from typing import Optional, List

from phi.cli.config import PhiCliConfig
from phi.cli.console import print_heading, print_info
from phi.infra.type import InfraType
from phi.infra.resources import InfraResources
from phi.workspace.config import WorkspaceConfig
from phi.utils.log import logger


def save_resources(
    phi_config: PhiCliConfig,
    ws_config: WorkspaceConfig,
    target_env: Optional[str] = None,
    target_group: Optional[str] = None,
    target_name: Optional[str] = None,
    target_type: Optional[str] = None,
) -> None:
    """Saves the K8s resources"""
    if ws_config is None:
        logger.error("WorkspaceConfig invalid")
        return

    # Set the local environment variables before processing configs
    ws_config.set_local_env()

    # Get resource groups to deploy
    resource_groups_to_save: List[InfraResources] = ws_config.get_resources(
        env=target_env,
        infra=InfraType.k8s,
        order="create",
    )

    # Track number of resource groups saved
    num_rgs_saved = 0
    num_rgs_to_save = len(resource_groups_to_save)
    # Track number of resources saved
    num_resources_saved = 0
    num_resources_to_save = 0

    if num_rgs_to_save == 0:
        print_info("No resources to save")
        return

    logger.debug(f"Processing {num_rgs_to_save} resource groups")
    for rg in resource_groups_to_save:
        _num_resources_saved, _num_resources_to_save = rg.save_resources(
            group_filter=target_group,
            name_filter=target_name,
            type_filter=target_type,
        )
        if _num_resources_saved > 0:
            num_rgs_saved += 1
        num_resources_saved += _num_resources_saved
        num_resources_to_save += _num_resources_to_save
        logger.debug(f"Saved {num_resources_saved} resources in {num_rgs_saved} resource groups")

    if num_resources_saved == 0:
        return

    print_heading(f"\n--**-- ResourceGroups saved: {num_rgs_saved}/{num_rgs_to_save}\n")

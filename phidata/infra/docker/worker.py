from collections import OrderedDict
from typing import Optional, List, Dict, Tuple

from phidata.infra.docker.args import DockerArgs
from phidata.infra.docker.api_client import DockerApiClient
from phidata.infra.docker.resource.base import DockerResource
from phidata.infra.docker.resource.group import (
    DockerResourceGroup,
    DockerBuildContext,
)
from phidata.infra.docker.resource.utils import (
    filter_and_flatten_docker_resource_groups,
    get_docker_resources_from_group,
)
from phidata.infra.docker.exceptions import (
    DockerArgsException,
    DockerApiClientException,
    DockerResourceCreationFailedException,
)
from phidata.utils.common import is_empty
from phidata.utils.cli_console import (
    print_info,
    print_info,
    print_heading,
    print_subheading,
    print_error,
    print_warning,
    confirm_yes_no,
)
from phidata.utils.log import logger


class DockerWorker:
    """This class interacts with the Docker API on behalf of phidata and DockerManager."""

    def __init__(self, docker_args: DockerArgs) -> None:
        self.docker_args: DockerArgs = docker_args
        self.docker_client: DockerApiClient = DockerApiClient(
            base_url=self.docker_args.base_url
        )
        self.docker_resources: Optional[Dict[str, DockerResourceGroup]] = None
        logger.debug(f"**-+-** DockerWorker created")

    def is_client_initialized(self) -> bool:
        return self.docker_client.is_initialized()

    def are_resources_initialized(self) -> bool:
        if self.docker_resources is not None and len(self.docker_resources) > 0:
            return True
        return False

    def are_resources_active(self) -> bool:
        # TODO: fix this
        return False

    ######################################################
    ## Init Resources
    ######################################################

    def init_resources(self) -> None:
        """
        This function populates the self.docker_resources dictionary.

        Step 1: Convert each PhidataApp to DockerResourceGroups.
        Step 2: Convert any default resources from DockerConfig to a DockerResourceGroup
        Step 3: Add all DockerResourceGroups to the self.docker_resources dict
        """
        logger.debug("-*- Initializing DockerResourceGroups")

        # track the total number of DockerResourceGroups to build for validation
        apps_to_build = self.docker_args.apps
        resources_to_build = self.docker_args.resources

        num_apps = len(apps_to_build) if apps_to_build is not None else 0
        num_resources = len(resources_to_build) if resources_to_build is not None else 0
        num_rgs_to_build = num_apps + num_resources
        num_rgs_built = 0

        # Step 1: Convert each PhidataApp to DockerResourceGroups.
        if apps_to_build is not None and isinstance(apps_to_build, list):
            for app in apps_to_build:
                if app.args is None:
                    print_error("Args for App {} are None".format(app))
                    continue
                logger.debug("-*- App: {}".format(app.name))

                ######################################################################
                # NOTE: VERY IMPORTANT TO GET RIGHT
                # Pass down the paths and env
                # from  WorkspaceConfig -> DockerConfig -> PhidataApp
                ######################################################################

                app.workspace_root_path = self.docker_args.workspace_root_path
                app.workspace_config_file_path = (
                    self.docker_args.workspace_config_file_path
                )
                app.scripts_dir = self.docker_args.scripts_dir
                app.storage_dir = self.docker_args.storage_dir
                app.meta_dir = self.docker_args.meta_dir
                app.products_dir = self.docker_args.products_dir
                app.notebooks_dir = self.docker_args.notebooks_dir
                app.workspace_config_dir = self.docker_args.workspace_config_dir
                app.docker_env = self.docker_args.docker_env

                app_rgs: Optional[
                    Dict[str, DockerResourceGroup]
                ] = app.get_docker_resource_groups(
                    docker_build_context=DockerBuildContext(
                        network=self.docker_args.network
                    )
                )
                if app_rgs is not None:
                    if self.docker_resources is None:
                        self.docker_resources = OrderedDict()
                    self.docker_resources.update(app_rgs)
                    num_rgs_built += 1

        # Step 2: Convert any default resources from DockerConfig to a DockerResourceGroup
        if self.docker_args.default_resources_available():
            logger.debug("Adding default DockerResourceGroup")
            num_rgs_to_build += 1
            default_docker_rg = DockerResourceGroup(
                images=self.docker_args.images,
                containers=self.docker_args.containers,
                volumes=self.docker_args.volumes,
            )
            if self.docker_args.resources is None:
                self.docker_args.resources = []
            self.docker_args.resources.append(default_docker_rg)

        # Step 3: Add all DockerResourceGroups to the self.docker_resources dict
        if self.docker_args.resources is not None and isinstance(
            self.docker_args.resources, list
        ):
            for resource in self.docker_args.resources:
                if not resource.enabled:
                    print_info(f"{resource.name} disabled")
                    continue
                logger.debug("-*- Resource: {}".format(resource.name))

                if isinstance(resource, DockerResourceGroup):
                    if self.docker_resources is None:
                        self.docker_resources = OrderedDict()
                    self.docker_resources[resource.name] = resource
                    num_rgs_built += 1

        logger.debug(
            f"# DockerResourceGroups built: {num_rgs_built}/{num_rgs_to_build}"
        )

    ######################################################
    ## Create Resources
    ######################################################

    def create_resources(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        app_filter: Optional[str] = None,
        auto_confirm: Optional[bool] = False,
    ) -> bool:
        logger.debug("-*- Creating DockerResources")
        if self.docker_resources is None:
            self.init_resources()
            if self.docker_resources is None:
                print_info("No resources available")
                return False

        # A list of tuples with 3 parts
        #   1. Resource group name
        #   2. Resource group weight
        #   3. List of Resources in group after filters
        docker_resources_to_create: List[Tuple[str, int, List[DockerResource]]] = []
        for docker_rg_name, docker_rg in self.docker_resources.items():
            logger.debug(f"Processing: {docker_rg_name}")

            # skip disabled DockerResourceGroups
            if not docker_rg.enabled:
                continue

            # skip groups not matching app_filter if provided
            if app_filter is not None:
                if app_filter.lower() not in docker_rg_name.lower():
                    logger.debug(f"Skipping {docker_rg_name}")
                    continue

            docker_resources_in_group = get_docker_resources_from_group(
                docker_resource_group=docker_rg,
                name_filter=name_filter,
                type_filter=type_filter,
            )
            if len(docker_resources_in_group) > 0:
                docker_resources_to_create.append(
                    (docker_rg_name, docker_rg.weight, docker_resources_in_group)
                )

        if len(docker_resources_to_create) == 0:
            print_subheading("No DockerResources to create")
            return True

        docker_resources_to_create_sorted: List[
            Tuple[str, int, List[DockerResource]]
        ] = sorted(
            docker_resources_to_create,
            key=lambda x: x[1],
        )

        # Validate resources to be created
        group_number = 1
        resource_number = 0
        if not auto_confirm:
            print_heading("--**-- Confirm resources:")
            for (
                group_name,
                group_weight,
                resource_list,
            ) in docker_resources_to_create_sorted:
                print_subheading(f"\n{group_number}. {group_name}")
                resource_number += len(resource_list)
                group_number += 1
                for resource in resource_list:
                    print_info(
                        f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}"
                    )
            print_info(f"\nNetwork: {self.docker_args.network}")
            print_info(f"\nTotal {resource_number} resources")
            confirm = confirm_yes_no("\nConfirm deploy")
            if not confirm:
                print_info("Skipping deploy")
                return False

        # track the total number of DockerResources to create for validation
        num_resources_to_create: int = 0
        num_resources_created: int = 0

        for (
            group_name,
            group_weight,
            resource_list,
        ) in docker_resources_to_create_sorted:
            print_subheading(f"\n-*- {group_name}")
            num_resources_to_create += len(resource_list)
            for resource in resource_list:
                if resource:
                    print_info(
                        f"\n-==+==- {resource.get_resource_type()}: {resource.get_resource_name()}"
                    )
                    # logger.debug(resource)
                    try:
                        _resource_created = resource.create(
                            docker_client=self.docker_client
                        )
                        if _resource_created:
                            num_resources_created += 1
                    except Exception as e:
                        logger.error(
                            f"-==+==--> Resource {resource.get_resource_type()}: {resource.get_resource_name()} could not be created."
                        )
                        logger.error("Error: {}".format(e))
                        logger.error(
                            "Skipping resource creation, please fix and try again..."
                        )

        print_info(
            f"\n# Resources created: {num_resources_created}/{num_resources_to_create}"
        )
        if num_resources_to_create == num_resources_created:
            return True

        logger.error(
            f"Resources created: {num_resources_created} do not match Resources required: {num_resources_to_create}"
        )
        return False

    def create_resources_dry_run(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        app_filter: Optional[str] = None,
        auto_confirm: Optional[bool] = False,
    ) -> None:
        logger.debug("-*- Creating DockerResources")
        if self.docker_resources is None:
            self.init_resources()
            if self.docker_resources is None:
                print_info("No resources available")
                return

        # A list of tuples with 3 parts
        #   1. Resource group name
        #   2. Resource group weight
        #   3. List of Resources in group after filters
        docker_resources_to_create: List[Tuple[str, int, List[DockerResource]]] = []
        for docker_rg_name, docker_rg in self.docker_resources.items():
            logger.debug(f"Processing: {docker_rg_name}")

            # skip disabled DockerResourceGroups
            if not docker_rg.enabled:
                continue

            # skip groups not matching app_filter if provided
            if app_filter is not None:
                if app_filter.lower() not in docker_rg_name.lower():
                    logger.debug(f"Skipping {docker_rg_name}")
                    continue

            docker_resources_in_group = get_docker_resources_from_group(
                docker_resource_group=docker_rg,
                name_filter=name_filter,
                type_filter=type_filter,
            )
            if len(docker_resources_in_group) > 0:
                docker_resources_to_create.append(
                    (docker_rg_name, docker_rg.weight, docker_resources_in_group)
                )

        if len(docker_resources_to_create) == 0:
            print_info("No DockerResources to create")
            return

        docker_resources_to_create_sorted: List[
            Tuple[str, int, List[DockerResource]]
        ] = sorted(
            docker_resources_to_create,
            key=lambda x: x[1],
        )

        group_number = 1
        num_resources_to_create: int = 0
        print_heading("--**-- Docker resources:")
        for (
            group_name,
            group_weight,
            resource_list,
        ) in docker_resources_to_create_sorted:
            print_subheading(f"\n{group_number}. {group_name}")
            num_resources_to_create += len(resource_list)
            group_number += 1
            for resource in resource_list:
                print_info(
                    f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}"
                )
        print_info(f"\nNetwork: {self.docker_args.network}")
        print_info(f"\nTotal {num_resources_to_create} resources")

    ######################################################
    ## Get Resources
    ######################################################

    def get_resources(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> Optional[List[DockerResource]]:

        logger.debug("-*- Getting DockerResources")
        if self.docker_resources is None:
            self.init_resources()
            if self.docker_resources is None:
                print_info("No DockerResources available")
                return None

        docker_resources: Optional[
            List[DockerResource]
        ] = filter_and_flatten_docker_resource_groups(
            docker_resource_groups=self.docker_resources,
            name_filter=name_filter,
            type_filter=type_filter,
        )

        return docker_resources

    ######################################################
    ## Delete Resources
    ######################################################

    def delete_resources(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        app_filter: Optional[str] = None,
        auto_confirm: Optional[bool] = False,
    ) -> bool:
        logger.debug("-*- Deleting DockerResources")
        if self.docker_resources is None:
            self.init_resources()
            if self.docker_resources is None:
                print_info("No resources available")
                return False

        # A list of tuples with 3 parts
        #   1. Resource group name
        #   2. Resource group weight
        #   3. List of Resources in group after filters
        docker_resources_to_delete: List[Tuple[str, int, List[DockerResource]]] = []
        for docker_rg_name, docker_rg in self.docker_resources.items():
            logger.debug(f"Processing: {docker_rg_name}")

            # skip disabled DockerResourceGroups
            if not docker_rg.enabled:
                continue

            # skip groups not matching app_filter if provided
            if app_filter is not None:
                if app_filter.lower() not in docker_rg_name.lower():
                    logger.debug(f"Skipping {docker_rg_name}")
                    continue

            docker_resources_in_group = get_docker_resources_from_group(
                docker_resource_group=docker_rg,
                name_filter=name_filter,
                type_filter=type_filter,
            )
            if len(docker_resources_in_group) > 0:
                docker_resources_to_delete.append(
                    (docker_rg_name, docker_rg.weight, docker_resources_in_group)
                )

        if len(docker_resources_to_delete) == 0:
            print_subheading("No DockerResources to delete")
            return True

        docker_resources_to_delete_sorted: List[
            Tuple[str, int, List[DockerResource]]
        ] = sorted(
            docker_resources_to_delete,
            key=lambda x: x[1],
            reverse=True,
        )

        # Validate resources to be created
        group_number = 1
        resource_number = 0
        if not auto_confirm:
            print_heading("--**-- Confirm resources:")
            for (
                group_name,
                group_weight,
                resource_list,
            ) in docker_resources_to_delete_sorted:
                print_subheading(f"\n{group_number}. {group_name}")
                resource_number += len(resource_list)
                group_number += 1
                for resource in resource_list:
                    print_info(
                        f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}"
                    )
            print_info(f"\nNetwork: {self.docker_args.network}")
            print_info(f"\nTotal {resource_number} resources")
            confirm = confirm_yes_no("\nConfirm delete")
            if not confirm:
                print_info("Skipping delete")
                return False

        # track the total number of DockerResources to create for validation
        num_resources_to_delete: int = 0
        num_resources_deleted: int = 0

        for (
            group_name,
            group_weight,
            resource_list,
        ) in docker_resources_to_delete_sorted:
            print_subheading(f"\n-*- {group_name}")
            num_resources_to_delete += len(resource_list)
            for resource in resource_list:
                if resource:
                    print_info(
                        f"\n-==+==- {resource.get_resource_type()}: {resource.get_resource_name()}"
                    )
                    # logger.debug(resource)
                    try:
                        _resource_created = resource.create(
                            docker_client=self.docker_client
                        )
                        if _resource_created:
                            num_resources_deleted += 1
                    except Exception as e:
                        logger.error(
                            f"-==+==--> Resource {resource.get_resource_type()}: {resource.get_resource_name()} could not be created."
                        )
                        logger.error("Error: {}".format(e))
                        logger.error(
                            "Skipping resource creation, please fix and try again..."
                        )

        print_info(
            f"\n# Resources deleted: {num_resources_deleted}/{num_resources_to_delete}"
        )
        if num_resources_to_delete == num_resources_deleted:
            return True

        logger.error(
            f"Resources deleted: {num_resources_deleted} do not match resources required: {num_resources_to_delete}"
        )
        return False

    def delete_resources_dry_run(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        app_filter: Optional[str] = None,
        auto_confirm: Optional[bool] = False,
    ) -> None:
        logger.debug("-*- Deleting DockerResources")
        if self.docker_resources is None:
            self.init_resources()
            if self.docker_resources is None:
                print_info("No resources available")
                return

        # A list of tuples with 3 parts
        #   1. Resource group name
        #   2. Resource group weight
        #   3. List of Resources in group after filters
        docker_resources_to_delete: List[Tuple[str, int, List[DockerResource]]] = []
        for docker_rg_name, docker_rg in self.docker_resources.items():
            logger.debug(f"Processing: {docker_rg_name}")

            # skip disabled DockerResourceGroups
            if not docker_rg.enabled:
                continue

            # skip groups not matching app_filter if provided
            if app_filter is not None:
                if app_filter.lower() not in docker_rg_name.lower():
                    logger.debug(f"Skipping {docker_rg_name}")
                    continue

            docker_resources_in_group = get_docker_resources_from_group(
                docker_resource_group=docker_rg,
                name_filter=name_filter,
                type_filter=type_filter,
            )
            if len(docker_resources_in_group) > 0:
                docker_resources_to_delete.append(
                    (docker_rg_name, docker_rg.weight, docker_resources_in_group)
                )

        if len(docker_resources_to_delete) == 0:
            print_info("No DockerResources to create")
            return

        docker_resources_to_delete_sorted: List[
            Tuple[str, int, List[DockerResource]]
        ] = sorted(
            docker_resources_to_delete,
            key=lambda x: x[1],
            reverse=True,
        )

        group_number = 1
        num_resources_to_delete: int = 0
        print_heading("--**-- Docker resources:")
        for (
            group_name,
            group_weight,
            resource_list,
        ) in docker_resources_to_delete_sorted:
            print_subheading(f"\n{group_number}. {group_name}")
            num_resources_to_delete += len(resource_list)
            group_number += 1
            for resource in resource_list:
                print_info(
                    f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}"
                )
        print_info(f"\nNetwork: {self.docker_args.network}")
        print_info(f"\nTotal {num_resources_to_delete} resources")

    ######################################################
    ## Patch Resources
    ######################################################

    def patch_resources(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        app_filter: Optional[str] = None,
        auto_confirm: Optional[bool] = False,
    ) -> bool:
        logger.debug("-*- Patching DockerResources")
        if self.docker_resources is None:
            self.init_resources()
            if self.docker_resources is None:
                print_info("No resources available")
                return False

        # A list of tuples with 3 parts
        #   1. Resource group name
        #   2. Resource group weight
        #   3. List of Resources in group after filters
        docker_resources_to_patch: List[Tuple[str, int, List[DockerResource]]] = []
        for docker_rg_name, docker_rg in self.docker_resources.items():
            logger.debug(f"Processing: {docker_rg_name}")

            # skip disabled DockerResourceGroups
            if not docker_rg.enabled:
                continue

            # skip groups not matching app_filter if provided
            if app_filter is not None:
                if app_filter.lower() not in docker_rg_name.lower():
                    logger.debug(f"Skipping {docker_rg_name}")
                    continue

            docker_resources_in_group = get_docker_resources_from_group(
                docker_resource_group=docker_rg,
                name_filter=name_filter,
                type_filter=type_filter,
            )
            if len(docker_resources_in_group) > 0:
                docker_resources_to_patch.append(
                    (docker_rg_name, docker_rg.weight, docker_resources_in_group)
                )

        if len(docker_resources_to_patch) == 0:
            print_subheading("No DockerResources to patch")
            return True

        docker_resources_to_patch_sorted: List[
            Tuple[str, int, List[DockerResource]]
        ] = sorted(
            docker_resources_to_patch,
            key=lambda x: x[1],
        )

        # Validate resources to be patched
        group_number = 1
        resource_number = 0
        if not auto_confirm:
            print_heading("--**-- Confirm resources:")
            for (
                group_name,
                group_weight,
                resource_list,
            ) in docker_resources_to_patch_sorted:
                print_subheading(f"\n{group_number}. {group_name}")
                resource_number += len(resource_list)
                group_number += 1
                for resource in resource_list:
                    print_info(
                        f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}"
                    )
            print_info(f"\nNetwork: {self.docker_args.network}")
            print_info(f"\nTotal {resource_number} resources")
            confirm = confirm_yes_no("\nConfirm patch")
            if not confirm:
                print_info("Skipping patch")
                return False

        # track the total number of DockerResources to patch for validation
        num_resources_to_patch: int = 0
        num_resources_patched: int = 0

        for (
            group_name,
            group_weight,
            resource_list,
        ) in docker_resources_to_patch_sorted:
            print_subheading(f"\n-*- {group_name}")
            num_resources_to_patch += len(resource_list)
            for resource in resource_list:
                if resource:
                    print_info(
                        f"\n-==+==- {resource.get_resource_type()}: {resource.get_resource_name()}"
                    )
                    # logger.debug(resource)
                    try:
                        _resource_patched = resource.update(
                            docker_client=self.docker_client
                        )
                        if _resource_patched:
                            num_resources_patched += 1
                    except Exception as e:
                        logger.error(
                            f"-==+==--> Resource {resource.get_resource_type()}: {resource.get_resource_name()} could not be patched."
                        )
                        logger.error("Error: {}".format(e))
                        logger.error(
                            "Skipping resource creation, please fix and try again..."
                        )

        print_info(
            f"\n# Resources patched: {num_resources_patched}/{num_resources_to_patch}"
        )
        if num_resources_to_patch == num_resources_patched:
            return True

        logger.error(
            f"Resources patched: {num_resources_patched} do not match resources required: {num_resources_to_patch}"
        )
        return False

    def patch_resources_dry_run(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        app_filter: Optional[str] = None,
        auto_confirm: Optional[bool] = False,
    ) -> None:
        logger.debug("-*- Patching DockerResources")
        if self.docker_resources is None:
            self.init_resources()
            if self.docker_resources is None:
                print_info("No resources available")
                return

        # A list of tuples with 3 parts
        #   1. Resource group name
        #   2. Resource group weight
        #   3. List of Resources in group after filters
        docker_resources_to_patch: List[Tuple[str, int, List[DockerResource]]] = []
        for docker_rg_name, docker_rg in self.docker_resources.items():
            logger.debug(f"Processing: {docker_rg_name}")

            # skip disabled DockerResourceGroups
            if not docker_rg.enabled:
                continue

            # skip groups not matching app_filter if provided
            if app_filter is not None:
                if app_filter.lower() not in docker_rg_name.lower():
                    logger.debug(f"Skipping {docker_rg_name}")
                    continue

            docker_resources_in_group = get_docker_resources_from_group(
                docker_resource_group=docker_rg,
                name_filter=name_filter,
                type_filter=type_filter,
            )
            if len(docker_resources_in_group) > 0:
                docker_resources_to_patch.append(
                    (docker_rg_name, docker_rg.weight, docker_resources_in_group)
                )

        if len(docker_resources_to_patch) == 0:
            print_info("No DockerResources to patch")
            return

        docker_resources_to_patch_sorted: List[
            Tuple[str, int, List[DockerResource]]
        ] = sorted(
            docker_resources_to_patch,
            key=lambda x: x[1],
        )

        group_number = 1
        num_resources_to_patch: int = 0
        print_heading("--**-- Docker resources:")
        for (
            group_name,
            group_weight,
            resource_list,
        ) in docker_resources_to_patch_sorted:
            print_subheading(f"\n{group_number}. {group_name}")
            num_resources_to_patch += len(resource_list)
            group_number += 1
            for resource in resource_list:
                print_info(
                    f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}"
                )
        print_info(f"\nNetwork: {self.docker_args.network}")
        print_info(f"\nTotal {num_resources_to_patch} resources")

    ######################################################
    ## End
    ######################################################

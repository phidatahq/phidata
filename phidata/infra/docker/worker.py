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
    """This class interacts with the Docker API."""

    def __init__(self, docker_args: DockerArgs) -> None:
        self.docker_args: DockerArgs = docker_args
        self.docker_client: DockerApiClient = DockerApiClient(
            base_url=self.docker_args.base_url
        )
        logger.debug(f"**-+-** DockerWorker created")

    def is_client_initialized(self) -> bool:
        return self.docker_client.is_initialized()

    def are_resources_active(self) -> bool:
        # TODO: fix this
        return False

    ######################################################
    ## Build Resources
    ######################################################

    def build_docker_resource_groups(
        self, app_filter: Optional[str] = None
    ) -> Optional[Dict[str, DockerResourceGroup]]:
        """
        Build the DockerResourceGroups for the requested apps

        Step 1: Convert each PhidataApp to DockerResourceGroups.
        Step 2: Convert any default resources from DockerConfig to a DockerResourceGroup
        Step 3: Add all DockerResourceGroups to the self.docker_resources dict
        """
        logger.debug("-*- Initializing DockerResourceGroups")

        docker_resource_groups: Optional[Dict[str, DockerResourceGroup]] = None

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

                if not app.enabled:
                    logger.debug(f"{app.name} disabled")
                    num_rgs_built += 1
                    continue

                # skip groups not matching app_filter if provided
                if app_filter is not None:
                    if app_filter.lower() not in app.name:
                        logger.debug(f"Skipping {app.name}")
                        num_rgs_built += 1
                        continue

                logger.debug("-*- App: {}".format(app.name))

                ######################################################################
                # NOTE: VERY IMPORTANT TO GET RIGHT
                # Pass down parameters from DockerArgs -> PhidataApp
                # The DockerConfig inherits these params from the WorkspaceConfig
                # 1. Pass down the paths from the WorkspaceConfig
                # 2. Pass down docker_env
                # 3. Pass down common cloud configuration. eg: aws_region, aws_profile
                # This should match phidata.infra.prep_infra_config.prep_infra_config()
                ######################################################################

                # -*- Path parameters
                app.scripts_dir = self.docker_args.scripts_dir
                app.storage_dir = self.docker_args.storage_dir
                app.meta_dir = self.docker_args.meta_dir
                app.products_dir = self.docker_args.products_dir
                app.notebooks_dir = self.docker_args.notebooks_dir
                app.workflows_dir = self.docker_args.workflows_dir
                # The ws_root_path is the ROOT directory for the workspace
                app.workspace_root_path = self.docker_args.workspace_root_path
                app.workspace_config_dir = self.docker_args.workspace_config_dir
                app.workspace_config_file_path = (
                    self.docker_args.workspace_config_file_path
                )

                # -*- Environment parameters
                # only update the params if they are not available on the app.
                # so we can prefer the app param if provided
                if app.docker_env is None and self.docker_args.docker_env is not None:
                    app.docker_env = self.docker_args.docker_env

                # -*- AWS parameters
                # only update the params if they are not available on the app.
                # so we can prefer the app param if provided
                if app.aws_region is None and self.docker_args.aws_region is not None:
                    app.aws_region = self.docker_args.aws_region
                if app.aws_profile is None and self.docker_args.aws_profile is not None:
                    app.aws_profile = self.docker_args.aws_profile
                if (
                    app.aws_config_file is None
                    and self.docker_args.aws_config_file is not None
                ):
                    app.aws_config_file = self.docker_args.aws_config_file
                if (
                    app.aws_shared_credentials_file is None
                    and self.docker_args.aws_shared_credentials_file is not None
                ):
                    app.aws_shared_credentials_file = (
                        self.docker_args.aws_shared_credentials_file
                    )

                app_rgs: Optional[
                    Dict[str, DockerResourceGroup]
                ] = app.get_docker_resource_groups(
                    docker_build_context=DockerBuildContext(
                        network=self.docker_args.network
                    )
                )
                if app_rgs is not None:
                    if docker_resource_groups is None:
                        docker_resource_groups = OrderedDict()
                    docker_resource_groups.update(app_rgs)
                    num_rgs_built += 1

        # Step 2: Convert any default resources from DockerConfig to a DockerResourceGroup
        if self.docker_args.default_resources_available():
            logger.debug("Adding default DockerResourceGroup")
            num_rgs_to_build += 1
            default_docker_rg = DockerResourceGroup(
                # weight=10,
                images=self.docker_args.images,
                containers=self.docker_args.containers,
                volumes=self.docker_args.volumes,
            )
            if self.docker_args.resources is None:
                self.docker_args.resources = []
            self.docker_args.resources.append(default_docker_rg)

        # Step 3: Add all DockerResourceGroups to the docker_resource_groups dict
        if self.docker_args.resources is not None and isinstance(
            self.docker_args.resources, list
        ):
            for resource in self.docker_args.resources:
                if not resource.enabled:
                    logger.debug(f"{resource.name} disabled")
                    num_rgs_built += 1
                    continue

                # skip groups not matching app_filter if provided
                if app_filter is not None:
                    if app_filter.lower() not in resource.name:
                        logger.debug(f"Skipping {resource.name}")
                        num_rgs_built += 1
                        continue

                logger.debug("-*- Resource: {}".format(resource.name))

                if isinstance(resource, DockerResourceGroup):
                    if docker_resource_groups is None:
                        docker_resource_groups = OrderedDict()
                    docker_resource_groups[resource.name] = resource
                    num_rgs_built += 1

        logger.debug(
            f"# DockerResourceGroups built: {num_rgs_built}/{num_rgs_to_build}"
        )
        return docker_resource_groups

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

        docker_resource_groups: Optional[
            Dict[str, DockerResourceGroup]
        ] = self.build_docker_resource_groups(app_filter=app_filter)

        if docker_resource_groups is None:
            print_info("No resources available")
            return True

        docker_resources_to_create: List[
            DockerResource
        ] = filter_and_flatten_docker_resource_groups(
            docker_resource_groups=docker_resource_groups,
            name_filter=name_filter,
            type_filter=type_filter,
            app_filter=app_filter,
        )

        # Validate resources to be created
        if not auto_confirm:
            print_heading("--**-- Confirm resources:")
            for resource in docker_resources_to_create:
                print_info(
                    f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}"
                )
            print_info(f"\nNetwork: {self.docker_args.network}")
            print_info(f"\nTotal {len(docker_resources_to_create)} resources")
            confirm = confirm_yes_no("\nConfirm deploy")
            if not confirm:
                print_info("-*-")
                print_info("-*- Skipping deploy")
                print_info("-*-")
                return False

        # track the total number of DockerResources to create for validation
        num_resources_to_create: int = len(docker_resources_to_create)
        num_resources_created: int = 0

        for resource in docker_resources_to_create:
            print_info(
                f"\n-==+==- {resource.get_resource_type()}: {resource.get_resource_name()}"
            )
            # logger.debug(resource)
            try:
                _resource_created = resource.create(docker_client=self.docker_client)
                if _resource_created:
                    num_resources_created += 1
                    print_info("Resource created")
                else:
                    logger.error(
                        f"Resource {resource.get_resource_type()}: {resource.get_resource_name()} could not be created."
                    )
                    if not self.docker_args.continue_on_create_failure:
                        return False
            except Exception as e:
                logger.error(
                    f"-==+==--> Resource {resource.get_resource_type()}: {resource.get_resource_name()} could not be created."
                )
                logger.error("Error: {}".format(e))
                logger.error("Skipping resource creation, please fix and try again...")

        print_info(
            f"\n# Resources created: {num_resources_created}/{num_resources_to_create}"
        )
        if num_resources_to_create == num_resources_created:
            return True

        logger.error(
            f"Resources created: {num_resources_created} do not match resources required: {num_resources_to_create}"
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

        docker_resource_groups: Optional[
            Dict[str, DockerResourceGroup]
        ] = self.build_docker_resource_groups(app_filter=app_filter)

        if docker_resource_groups is None:
            print_info("No resources available")
            return

        docker_resources_to_create: List[
            DockerResource
        ] = filter_and_flatten_docker_resource_groups(
            docker_resource_groups=docker_resource_groups,
            name_filter=name_filter,
            type_filter=type_filter,
            app_filter=app_filter,
        )

        num_resources_to_create: int = len(docker_resources_to_create)
        print_heading("--**-- Docker resources:")
        for resource in docker_resources_to_create:
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
        app_filter: Optional[str] = None,
    ) -> Optional[List[DockerResource]]:

        logger.debug("-*- Getting DockerResources")

        docker_resource_groups: Optional[
            Dict[str, DockerResourceGroup]
        ] = self.build_docker_resource_groups(app_filter=app_filter)

        if docker_resource_groups is None:
            print_info("No resources available")
            return None

        docker_resources: List[
            DockerResource
        ] = filter_and_flatten_docker_resource_groups(
            docker_resource_groups=docker_resource_groups,
            name_filter=name_filter,
            type_filter=type_filter,
            app_filter=app_filter,
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

        docker_resource_groups: Optional[
            Dict[str, DockerResourceGroup]
        ] = self.build_docker_resource_groups(app_filter=app_filter)

        if docker_resource_groups is None:
            print_info("No resources available")
            return True

        docker_resources_to_delete: List[
            DockerResource
        ] = filter_and_flatten_docker_resource_groups(
            docker_resource_groups=docker_resource_groups,
            name_filter=name_filter,
            type_filter=type_filter,
            app_filter=app_filter,
            sort_order="delete",
        )

        # Validate resources to be deleted
        if not auto_confirm:
            print_heading("--**-- Confirm resources:")
            for resource in docker_resources_to_delete:
                print_info(
                    f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}"
                )
            print_info(f"\nNetwork: {self.docker_args.network}")
            print_info(f"\nTotal {len(docker_resources_to_delete)} resources")
            confirm = confirm_yes_no("\nConfirm delete")
            if not confirm:
                print_info("Skipping delete")
                return False

        # track the total number of DockerResources to delete for validation
        num_resources_to_delete: int = len(docker_resources_to_delete)
        num_resources_deleted: int = 0

        for resource in docker_resources_to_delete:
            print_info(
                f"\n-==+==- {resource.get_resource_type()}: {resource.get_resource_name()}"
            )
            # logger.debug(resource)
            try:
                _resource_deleted = resource.delete(docker_client=self.docker_client)
                if _resource_deleted:
                    num_resources_deleted += 1
                    print_info("Resource deleted")
                else:
                    logger.error(
                        f"Resource {resource.get_resource_type()}: {resource.get_resource_name()} could not be deleted."
                    )
                    if not self.docker_args.continue_on_delete_failure:
                        return False
            except Exception as e:
                logger.error(
                    f"-==+==--> Resource {resource.get_resource_type()}: {resource.get_resource_name()} could not be deleted."
                )
                logger.error("Error: {}".format(e))
                logger.error("Skipping resource creation, please fix and try again...")

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

        docker_resource_groups: Optional[
            Dict[str, DockerResourceGroup]
        ] = self.build_docker_resource_groups(app_filter=app_filter)

        if docker_resource_groups is None:
            print_info("No resources available")
            return

        docker_resources_to_delete: List[
            DockerResource
        ] = filter_and_flatten_docker_resource_groups(
            docker_resource_groups=docker_resource_groups,
            name_filter=name_filter,
            type_filter=type_filter,
            app_filter=app_filter,
            sort_order="delete",
        )

        num_resources_to_delete: int = len(docker_resources_to_delete)
        print_heading("--**-- Docker resources:")
        for resource in docker_resources_to_delete:
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

        docker_resource_groups: Optional[
            Dict[str, DockerResourceGroup]
        ] = self.build_docker_resource_groups(app_filter=app_filter)

        if docker_resource_groups is None:
            print_info("No resources available")
            return True

        docker_resources_to_patch: List[
            DockerResource
        ] = filter_and_flatten_docker_resource_groups(
            docker_resource_groups=docker_resource_groups,
            name_filter=name_filter,
            type_filter=type_filter,
            app_filter=app_filter,
        )

        # Validate resources to be patched
        if not auto_confirm:
            print_heading("--**-- Confirm resources:")
            for resource in docker_resources_to_patch:
                print_info(
                    f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}"
                )
            print_info(f"\nNetwork: {self.docker_args.network}")
            print_info(f"\nTotal {len(docker_resources_to_patch)} resources")
            confirm = confirm_yes_no("\nConfirm patch")
            if not confirm:
                print_info("Skipping patch")
                return False

        # track the total number of DockerResources to patch for validation
        num_resources_to_patch: int = len(docker_resources_to_patch)
        num_resources_patched: int = 0

        for resource in docker_resources_to_patch:
            print_info(
                f"\n-==+==- {resource.get_resource_type()}: {resource.get_resource_name()}"
            )
            # logger.debug(resource)
            try:
                _resource_patched = resource.update(docker_client=self.docker_client)
                if _resource_patched:
                    num_resources_patched += 1
                    print_info("Resource patched")
                else:
                    logger.error(
                        f"Resource {resource.get_resource_type()}: {resource.get_resource_name()} could not be patched."
                    )
                    if not self.docker_args.continue_on_patch_failure:
                        return False
            except Exception as e:
                logger.error(
                    f"-==+==--> Resource {resource.get_resource_type()}: {resource.get_resource_name()} could not be patched."
                )
                logger.error("Error: {}".format(e))
                logger.error("Skipping resource creation, please fix and try again...")

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

        docker_resource_groups: Optional[
            Dict[str, DockerResourceGroup]
        ] = self.build_docker_resource_groups(app_filter=app_filter)

        if docker_resource_groups is None:
            print_info("No resources available")
            return

        docker_resources_to_patch: List[
            DockerResource
        ] = filter_and_flatten_docker_resource_groups(
            docker_resource_groups=docker_resource_groups,
            name_filter=name_filter,
            type_filter=type_filter,
            app_filter=app_filter,
        )

        num_resources_to_patch: int = len(docker_resources_to_patch)
        print_heading("--**-- Docker resources:")
        for resource in docker_resources_to_patch:
            print_info(
                f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}"
            )
        print_info(f"\nNetwork: {self.docker_args.network}")
        print_info(f"\nTotal {num_resources_to_patch} resources")

    ######################################################
    ## End
    ######################################################

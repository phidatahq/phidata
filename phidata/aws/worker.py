from collections import OrderedDict
from typing import Dict, List, Optional, Union

from phidata.aws.args import AwsArgs
from phidata.app.base_app import BaseApp
from phidata.app.phidata_app import PhidataApp
from phidata.aws.api_client import AwsApiClient
from phidata.aws.resource.base import AwsResource
from phidata.aws.resource.group import AwsResourceGroup
from phidata.aws.resource.utils import (
    filter_and_flatten_aws_resource_groups,
)
from phidata.utils.cli_console import (
    print_info,
    print_heading,
    confirm_yes_no,
)
from phidata.utils.log import logger


class AwsWorker:
    """This class interacts with the Aws API."""

    def __init__(self, aws_args: AwsArgs) -> None:
        self.aws_args: AwsArgs = aws_args
        self.aws_api_client: AwsApiClient = AwsApiClient(
            aws_region=self.aws_args.aws_region,
            aws_profile=self.aws_args.aws_profile,
        )
        logger.debug(f"**-+-** AwsWorker created")

    def is_client_initialized(self) -> bool:
        return self.aws_api_client.is_initialized()

    def are_resources_active(self) -> bool:
        # TODO: fix this
        return False

    ######################################################
    ## Build Resources
    ######################################################

    def build_aws_resource_groups(
        self,
        app_filter: Optional[str] = None,
    ) -> Optional[Dict[str, AwsResourceGroup]]:
        """
        Build the AwsResourceGroups for the requested apps
        """
        logger.debug("-*- Initializing AwsResourceGroups")

        aws_resource_groups: Optional[Dict[str, AwsResourceGroup]] = None

        aws_apps: Optional[List[Union[BaseApp, PhidataApp]]] = self.aws_args.apps
        aws_rgs: Optional[List[AwsResourceGroup]] = self.aws_args.resources

        num_apps = len(aws_apps) if aws_apps is not None else 0
        num_rgs = len(aws_rgs) if aws_rgs is not None else 0
        num_rgs_to_build = num_apps + num_rgs
        num_rgs_built = 0

        # Step 1: Convert each PhidataApp to AwsResourceGroup.
        if aws_apps is not None and isinstance(aws_apps, list):
            for app in aws_apps:
                if app.args is None:
                    logger.error("Args for App {} are None".format(app))
                    num_rgs_built += 1
                    continue

                if not app.enabled:
                    logger.debug(f"{app.name} disabled")
                    num_rgs_built += 1
                    continue

                # skip apps not matching app_filter if provided
                if app_filter is not None:
                    if app_filter.lower() not in app.name:
                        logger.debug(f"Skipping {app.name}")
                        num_rgs_built += 1
                        continue

                logger.debug("-*- App: {}".format(app.name))

                ######################################################################
                # NOTE: VERY IMPORTANT TO GET RIGHT
                # Pass down parameters from K8sArgs -> PhidataApp
                # The K8sConfig inherits these params from the WorkspaceConfig
                # 1. Pass down the paths from the WorkspaceConfig
                # 2. Pass down k8s_env
                # 3. Pass down common cloud configuration. eg: aws_region, aws_profile
                # This should match phidata.infra.prep_infra_config.prep_infra_config()
                ######################################################################

                # -*- Path parameters
                app.scripts_dir = self.aws_args.scripts_dir
                app.storage_dir = self.aws_args.storage_dir
                app.meta_dir = self.aws_args.meta_dir
                app.products_dir = self.aws_args.products_dir
                app.notebooks_dir = self.aws_args.notebooks_dir
                app.workflows_dir = self.aws_args.workflows_dir
                # The ws_root_path is the ROOT directory for the workspace
                app.workspace_root_path = self.aws_args.workspace_root_path
                app.workspace_config_dir = self.aws_args.workspace_config_dir
                app.workspace_config_file_path = (
                    self.aws_args.workspace_config_file_path
                )

                # -*- AWS parameters
                # only update the params if they are not available on the app.
                # so we can prefer the app param if provided
                if app.aws_region is None and self.aws_args.aws_region is not None:
                    app.aws_region = self.aws_args.aws_region
                if app.aws_profile is None and self.aws_args.aws_profile is not None:
                    app.aws_profile = self.aws_args.aws_profile
                if (
                    app.aws_config_file is None
                    and self.aws_args.aws_config_file is not None
                ):
                    app.aws_config_file = self.aws_args.aws_config_file
                if (
                    app.aws_shared_credentials_file is None
                    and self.aws_args.aws_shared_credentials_file is not None
                ):
                    app.aws_shared_credentials_file = (
                        self.aws_args.aws_shared_credentials_file
                    )

                app_rgs: Optional[
                    Dict[str, AwsResourceGroup]
                ] = app.get_aws_resource_groups(aws_build_context=self.aws_args)
                if app_rgs is not None:
                    if aws_resource_groups is None:
                        aws_resource_groups = OrderedDict()
                    aws_resource_groups.update(app_rgs)
                    num_rgs_built += 1

        # Step 2: Add all AwsResourceGroups to the aws_resource_groups dict
        if aws_rgs is not None and isinstance(aws_rgs, list):
            for rg in aws_rgs:
                if not rg.enabled:
                    logger.debug(f"{rg.name} disabled")
                    num_rgs_built += 1
                    continue

                # skip groups not matching app_filter if provided
                if app_filter is not None:
                    if app_filter.lower() not in rg.name:
                        logger.debug(f"Skipping {rg.name}")
                        num_rgs_built += 1
                        continue

                if isinstance(rg, AwsResourceGroup):
                    if aws_resource_groups is None:
                        aws_resource_groups = OrderedDict()
                    aws_resource_groups[rg.name] = rg
                    num_rgs_built += 1

        logger.debug(f"# AwsResourceGroups built: {num_rgs_built}/{num_rgs_to_build}")
        return aws_resource_groups

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
        logger.debug("-*- Creating AwsResources")

        aws_resource_groups: Optional[
            Dict[str, AwsResourceGroup]
        ] = self.build_aws_resource_groups(app_filter=app_filter)

        if aws_resource_groups is None:
            print_info("No resources available")
            return True

        aws_resources_to_create: List[
            AwsResource
        ] = filter_and_flatten_aws_resource_groups(
            aws_resource_groups=aws_resource_groups,
            name_filter=name_filter,
            type_filter=type_filter,
            app_filter=app_filter,
        )

        # Validate resources to be created
        if not auto_confirm:
            print_heading("--**-- Confirm resources:")
            for resource in aws_resources_to_create:
                print_info(
                    f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}"
                )
            if self.aws_args.aws_region:
                print_info(f"\nRegion: {self.aws_args.aws_region}")
            if self.aws_args.aws_profile:
                print_info(f"Profile: {self.aws_args.aws_profile}")
            print_info(f"\nTotal {len(aws_resources_to_create)} resources")
            confirm = confirm_yes_no("\nConfirm deploy")
            if not confirm:
                print_info("-*-")
                print_info("-*- Skipping deploy")
                print_info("-*-")
                exit(0)

        # track the total number of AwsResources to create for validation
        num_resources_to_create: int = len(aws_resources_to_create)
        num_resources_created: int = 0

        for resource in aws_resources_to_create:
            print_info(
                f"\n-==+==- {resource.get_resource_type()}: {resource.get_resource_name()}"
            )
            # logger.debug(resource)
            try:
                _resource_created = resource.create(aws_client=self.aws_api_client)
                if _resource_created:
                    num_resources_created += 1
                    print_info("Resource created")
                else:
                    logger.error(
                        f"Resource {resource.get_resource_type()}: {resource.get_resource_name()} could not be created."
                    )
                    if not self.aws_args.continue_on_create_failure:
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
        logger.debug("-*- Creating AwsResources")

        aws_resource_groups: Optional[
            Dict[str, AwsResourceGroup]
        ] = self.build_aws_resource_groups(app_filter=app_filter)

        if aws_resource_groups is None:
            print_info("No resources available")
            return

        aws_resources_to_create: List[
            AwsResource
        ] = filter_and_flatten_aws_resource_groups(
            aws_resource_groups=aws_resource_groups,
            name_filter=name_filter,
            type_filter=type_filter,
            app_filter=app_filter,
        )

        num_resources_to_create: int = len(aws_resources_to_create)
        print_heading("--**-- Aws resources:")
        for resource in aws_resources_to_create:
            print_info(
                f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}"
            )
        if self.aws_args.aws_region:
            print_info(f"\nRegion: {self.aws_args.aws_region}")
        if self.aws_args.aws_profile:
            print_info(f"Profile: {self.aws_args.aws_profile}")
        print_info(f"\nTotal {num_resources_to_create} resources")

    ######################################################
    ## Get Resources
    ######################################################

    def get_resources(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        app_filter: Optional[str] = None,
    ) -> Optional[List[AwsResource]]:
        logger.debug("-*- Getting AwsResources")

        aws_resource_groups: Optional[
            Dict[str, AwsResourceGroup]
        ] = self.build_aws_resource_groups(app_filter=app_filter)

        if aws_resource_groups is None:
            print_info("No resources available")
            return None

        aws_resources: List[AwsResource] = filter_and_flatten_aws_resource_groups(
            aws_resource_groups=aws_resource_groups,
            name_filter=name_filter,
            type_filter=type_filter,
            app_filter=app_filter,
        )

        return aws_resources

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
        logger.debug("-*- Deleting AwsResources")

        aws_resource_groups: Optional[
            Dict[str, AwsResourceGroup]
        ] = self.build_aws_resource_groups(app_filter=app_filter)

        if aws_resource_groups is None:
            print_info("No resources available")
            return True

        aws_resources_to_delete: List[
            AwsResource
        ] = filter_and_flatten_aws_resource_groups(
            aws_resource_groups=aws_resource_groups,
            name_filter=name_filter,
            type_filter=type_filter,
            app_filter=app_filter,
            sort_order="delete",
        )

        # Validate resources to be deleted
        if not auto_confirm:
            print_heading("--**-- Confirm resources:")
            for resource in aws_resources_to_delete:
                print_info(
                    f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}"
                )
            if self.aws_args.aws_region:
                print_info(f"\nRegion: {self.aws_args.aws_region}")
            if self.aws_args.aws_profile:
                print_info(f"Profile: {self.aws_args.aws_profile}")
            print_info(f"\nTotal {len(aws_resources_to_delete)} resources")
            confirm = confirm_yes_no("\nConfirm delete")
            if not confirm:
                print_info("-*-")
                print_info("-*- Skipping delete")
                print_info("-*-")
                exit(0)

        # track the total number of AwsResources to delete for validation
        num_resources_to_delete: int = len(aws_resources_to_delete)
        num_resources_deleted: int = 0

        for resource in aws_resources_to_delete:
            print_info(
                f"\n-==+==- {resource.get_resource_type()}: {resource.get_resource_name()}"
            )
            # logger.debug(resource)
            try:
                _resource_deleted = resource.delete(aws_client=self.aws_api_client)
                if _resource_deleted:
                    num_resources_deleted += 1
                    print_info("Resource deleted")
                else:
                    logger.error(
                        f"Resource {resource.get_resource_type()}: {resource.get_resource_name()} could not be deleted."
                    )
                    if not self.aws_args.continue_on_delete_failure:
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
        logger.debug("-*- Deleting AwsResources")

        aws_resource_groups: Optional[
            Dict[str, AwsResourceGroup]
        ] = self.build_aws_resource_groups(app_filter=app_filter)

        if aws_resource_groups is None:
            print_info("No resources available")
            return

        aws_resources_to_delete: List[
            AwsResource
        ] = filter_and_flatten_aws_resource_groups(
            aws_resource_groups=aws_resource_groups,
            name_filter=name_filter,
            type_filter=type_filter,
            app_filter=app_filter,
            sort_order="delete",
        )

        num_resources_to_delete: int = len(aws_resources_to_delete)
        print_heading("--**-- Aws resources:")
        for resource in aws_resources_to_delete:
            print_info(
                f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}"
            )
        if self.aws_args.aws_region:
            print_info(f"\nRegion: {self.aws_args.aws_region}")
        if self.aws_args.aws_profile:
            print_info(f"Profile: {self.aws_args.aws_profile}")
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
        logger.debug("-*- Patching AwsResources")

        aws_resource_groups: Optional[
            Dict[str, AwsResourceGroup]
        ] = self.build_aws_resource_groups(app_filter=app_filter)

        if aws_resource_groups is None:
            print_info("No resources available")
            return True

        aws_resources_to_patch: List[
            AwsResource
        ] = filter_and_flatten_aws_resource_groups(
            aws_resource_groups=aws_resource_groups,
            name_filter=name_filter,
            type_filter=type_filter,
            app_filter=app_filter,
        )

        # Validate resources to be patched
        if not auto_confirm:
            print_heading("--**-- Confirm resources:")
            for resource in aws_resources_to_patch:
                print_info(
                    f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}"
                )
            if self.aws_args.aws_region:
                print_info(f"\nRegion: {self.aws_args.aws_region}")
            if self.aws_args.aws_profile:
                print_info(f"Profile: {self.aws_args.aws_profile}")
            print_info(f"\nTotal {len(aws_resources_to_patch)} resources")
            confirm = confirm_yes_no("\nConfirm patch")
            if not confirm:
                print_info("-*-")
                print_info("-*- Skipping patch")
                print_info("-*-")
                exit(0)

        # track the total number of AwsResources to patch for validation
        num_resources_to_patch: int = len(aws_resources_to_patch)
        num_resources_patched: int = 0

        for resource in aws_resources_to_patch:
            print_info(
                f"\n-==+==- {resource.get_resource_type()}: {resource.get_resource_name()}"
            )
            # logger.debug(resource)
            try:
                _resource_patched = resource.update(aws_client=self.aws_api_client)
                if _resource_patched:
                    num_resources_patched += 1
                    print_info("Resource patched")
                else:
                    logger.error(
                        f"Resource {resource.get_resource_type()}: {resource.get_resource_name()} could not be patched."
                    )
                    if not self.aws_args.continue_on_patch_failure:
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
        logger.debug("-*- Patching AwsResources")

        aws_resource_groups: Optional[
            Dict[str, AwsResourceGroup]
        ] = self.build_aws_resource_groups(app_filter=app_filter)

        if aws_resource_groups is None:
            print_info("No resources available")
            return

        aws_resources_to_patch: List[
            AwsResource
        ] = filter_and_flatten_aws_resource_groups(
            aws_resource_groups=aws_resource_groups,
            name_filter=name_filter,
            type_filter=type_filter,
            app_filter=app_filter,
        )

        num_resources_to_patch: int = len(aws_resources_to_patch)
        print_heading("--**-- Aws resources:")
        for resource in aws_resources_to_patch:
            print_info(
                f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}"
            )
        if self.aws_args.aws_region:
            print_info(f"\nRegion: {self.aws_args.aws_region}")
        if self.aws_args.aws_profile:
            print_info(f"Profile: {self.aws_args.aws_profile}")
        print_info(f"\nTotal {num_resources_to_patch} resources")

    ######################################################
    ## End
    ######################################################

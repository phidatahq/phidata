from collections import OrderedDict
from typing import Dict, List, Optional

from phidata.infra.aws.args import AwsArgs
from phidata.infra.aws.api_client import AwsApiClient
from phidata.infra.aws.resource.base import AwsResource
from phidata.infra.aws.resource.group import AwsResourceGroup
from phidata.infra.aws.resource.utils import (
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

        aws_rgs: Optional[List[AwsResourceGroup]] = self.aws_args.resources

        num_rgs_to_build = len(aws_rgs) if aws_rgs is not None else 0
        num_rgs_built = 0

        if aws_rgs is not None and isinstance(aws_rgs, list):
            aws_resource_groups: Dict[str, AwsResourceGroup] = OrderedDict()

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
                    aws_resource_groups[rg.name] = rg
                    num_rgs_built += 1

            logger.debug(
                f"# AwsResourceGroups built: {num_rgs_built}/{num_rgs_to_build}"
            )
            return aws_resource_groups

        return None

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
                return False

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
                print_info("Skipping delete")
                return False

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
                print_info("Skipping patch")
                return False

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

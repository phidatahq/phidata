from collections import OrderedDict
from typing import Any, Dict, List, Optional, Type, Set, cast, Tuple

from phidata.infra.aws.args import AwsArgs
from phidata.infra.aws.api_client import AwsApiClient
from phidata.infra.aws.exceptions import (
    AwsArgsException,
    AwsApiClientException,
    AwsResourceCreationFailedException,
)
from phidata.infra.aws.resource.base import AwsResource
from phidata.infra.aws.resource.group import AwsResourceGroup
from phidata.infra.aws.resource.types import AwsResourceType
from phidata.infra.aws.resource.utils import (
    get_aws_resources_from_group,
    filter_and_flatten_aws_resource_groups,
)
from phidata.utils.cli_console import (
    print_info,
    print_info,
    print_heading,
    print_subheading,
    print_error,
    confirm_yes_no,
)
from phidata.utils.common import is_empty
from phidata.utils.log import logger


class AwsWorker:
    """This class interacts with the Aws API."""

    def __init__(self, aws_args: AwsArgs) -> None:
        self.aws_args: AwsArgs = aws_args
        self.aws_api_client: AwsApiClient = AwsApiClient(
            aws_region=self.aws_args.aws_region,
            aws_profile=self.aws_args.aws_profile,
        )
        self.aws_resources: Optional[Dict[str, AwsResourceGroup]] = None
        logger.debug(f"**-+-** AwsWorker created")

    def is_client_initialized(self) -> bool:
        return self.aws_api_client.is_initialized()

    def are_resources_initialized(self) -> bool:
        if self.aws_resources is not None and len(self.aws_resources) > 0:
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
        This function populates the self.aws_resources dictionary.
        """
        logger.debug("-*- Initializing AwsResourceGroup")

        if self.aws_resources is None:
            self.aws_resources = OrderedDict()

        rgs_to_build = self.aws_args.resources
        if rgs_to_build is not None and isinstance(rgs_to_build, list):
            for resource_group in rgs_to_build:
                self.aws_resources[resource_group.name] = resource_group

        logger.debug(f"# AwsResources built: {len(self.aws_resources)}")

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
        if self.aws_resources is None:
            self.init_resources()
            if self.aws_resources is None:
                print_info("No resources available")
                return False

        aws_resources_to_create: List[
            AwsResource
        ] = filter_and_flatten_aws_resource_groups(
            aws_resource_groups=self.aws_resources,
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
                print_info("Skipping deploy")
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
        if self.aws_resources is None:
            self.init_resources()
            if self.aws_resources is None:
                print_info("No resources available")
                return

        aws_resources_to_create: List[
            AwsResource
        ] = filter_and_flatten_aws_resource_groups(
            aws_resource_groups=self.aws_resources,
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
        if self.aws_resources is None:
            self.init_resources()
            if self.aws_resources is None:
                print_info("No AwsResources available")
                return None

        aws_resources: List[AwsResource] = filter_and_flatten_aws_resource_groups(
            aws_resource_groups=self.aws_resources,
            name_filter=name_filter,
            type_filter=type_filter,
            app_filter=app_filter,
        )

        return aws_resources

    def get_resource_groups(self) -> Optional[Dict[str, AwsResourceGroup]]:
        logger.debug("-*- Getting AwsResourceGroups")
        if self.aws_resources is None:
            self.init_resources()
            if self.aws_resources is None:
                print_info("No AwsResources available")
                return {}

        return self.aws_resources

    ######################################################
    ## Read Resources
    ######################################################

    def read_resources(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        app_filter: Optional[str] = None,
    ) -> Optional[List[AwsResource]]:

        logger.debug("-*- Getting AwsResources")
        if self.aws_resources is None:
            self.init_resources()
            if self.aws_resources is None:
                print_info("No resources available")
                return None

        aws_resources: Optional[
            List[AwsResource]
        ] = filter_and_flatten_aws_resource_groups(
            aws_resource_groups=self.aws_resources,
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
        if self.aws_resources is None:
            self.init_resources()
            if self.aws_resources is None:
                print_info("No resources available")
                return False

        aws_resources_to_delete: List[
            AwsResource
        ] = filter_and_flatten_aws_resource_groups(
            aws_resource_groups=self.aws_resources,
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
        if self.aws_resources is None:
            self.init_resources()
            if self.aws_resources is None:
                print_info("No resources available")
                return

        aws_resources_to_delete: List[
            AwsResource
        ] = filter_and_flatten_aws_resource_groups(
            aws_resource_groups=self.aws_resources,
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
        if self.aws_resources is None:
            self.init_resources()
            if self.aws_resources is None:
                print_info("No resources available")
                return False

        aws_resources_to_patch: List[
            AwsResource
        ] = filter_and_flatten_aws_resource_groups(
            aws_resource_groups=self.aws_resources,
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
        if self.aws_resources is None:
            self.init_resources()
            if self.aws_resources is None:
                print_info("No resources available")
                return

        aws_resources_to_patch: List[
            AwsResource
        ] = filter_and_flatten_aws_resource_groups(
            aws_resource_groups=self.aws_resources,
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

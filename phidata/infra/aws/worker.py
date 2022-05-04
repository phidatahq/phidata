from collections import defaultdict, OrderedDict
from typing import Any, Dict, List, Optional, Type, Set, cast

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
from phidata.infra.aws.resource.utils import filter_and_flatten_aws_resource_group
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
        # logger.debug(f"Creating AwsWorker")
        if aws_args is None or not isinstance(aws_args, AwsArgs):
            raise AwsArgsException("AwsArgs invalid: {}".format(aws_args))

        self.aws_args: AwsArgs = aws_args
        self.aws_api_client: AwsApiClient = AwsApiClient(
            aws_region=self.aws_args.aws_region,
            aws_profile=self.aws_args.aws_profile,
        )
        self.aws_resource_group: Optional[AwsResourceGroup] = None
        logger.debug(f"**-+-** AwsWorker created")

    def is_client_initialized(self) -> bool:
        return self.aws_api_client.is_initialized()

    def are_resources_initialized(self) -> bool:
        return True if self.aws_resource_group is not None else False

    ######################################################
    ## Init Resources
    ######################################################

    def init_resources(self) -> None:
        """
        This function populates the self.aws_resource_group dictionary.
        """
        logger.debug("-*- Initializing AwsResources")

        if self.aws_args.resources is not None and isinstance(
            self.aws_args.resources, AwsResourceGroup
        ):
            self.aws_resource_group = self.aws_args.resources
        logger.debug(f"-*- AwsResources built")

    ######################################################
    ## Create Resources
    ######################################################

    def create_resources(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> bool:
        logger.debug("-*- Creating AwsResources")
        if self.aws_resource_group is None:
            self.init_resources()
            if self.aws_resource_group is None:
                print_info("No AwsResources available")
                return False

        aws_resources_to_create: Optional[
            List[AwsResourceType]
        ] = filter_and_flatten_aws_resource_group(
            aws_resource_group=self.aws_resource_group,
            name_filter=name_filter,
            type_filter=type_filter,
            sort_order="create",
        )
        if aws_resources_to_create is None or is_empty(aws_resources_to_create):
            print_info("No AwsResources to create")
            return True

        # track the total number of AwsResources to create for validation
        num_resources_to_create: int = len(aws_resources_to_create)
        num_resources_created: int = 0

        # Print the resources for validation
        print_subheading(f"Creating {num_resources_to_create} AwsResources:")
        for rsrc in aws_resources_to_create:
            print_info(f"  -+-> {rsrc.get_resource_type()}: {rsrc.get_resource_name()}")
        confirm = confirm_yes_no("\nConfirm deploy")
        if not confirm:
            print_info("Skipping deploy")
            return False

        for resource in aws_resources_to_create:
            if resource:
                print_info(
                    f"\n-==+==- {resource.get_resource_type()}: {resource.get_resource_name()}"
                )
                # logger.debug(resource)
                try:
                    _resource_created = resource.create(aws_client=self.aws_api_client)
                    if _resource_created:
                        num_resources_created += 1
                except Exception as e:
                    print_error(
                        f"-==+==--> Resource {resource.get_resource_type()}: {resource.get_resource_name()} could not be created."
                    )
                    print_error("Error: {}".format(e))
                    print_error(
                        "Skipping resource creation, please fix and try again..."
                    )

        print_info(
            f"\n# Resources created: {num_resources_created}/{num_resources_to_create}"
        )
        if num_resources_to_create == num_resources_created:
            return True

        print_error(
            f"Resources created: {num_resources_created} do not match Resources required: {num_resources_to_create}"
        )
        return False

    def create_resources_dry_run(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> None:

        env = self.aws_args.env
        print_subheading(
            "AwsResources{}".format(f" for env: {env}" if env is not None else "")
        )
        if self.aws_resource_group is None:
            self.init_resources()
            if self.aws_resource_group is None:
                print_info("No AwsResources available")
                return

        aws_resources_to_create: Optional[
            List[AwsResourceType]
        ] = filter_and_flatten_aws_resource_group(
            aws_resource_group=self.aws_resource_group,
            name_filter=name_filter,
            type_filter=type_filter,
            sort_order="create",
        )
        if aws_resources_to_create is None or is_empty(aws_resources_to_create):
            print_info("No AwsResources to create")
            return

        num_resources_to_create: int = len(aws_resources_to_create)
        print_info(
            f"\n-*- Deploying this AwsConfig will create {num_resources_to_create} resources:"
        )
        for resource in aws_resources_to_create:
            print_info(
                f"-==+==- {resource.__class__.__name__}: {resource.get_resource_name()}"
            )

    ######################################################
    ## Read Resources
    ######################################################

    def read_resources(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> Dict[str, List[AwsResourceType]]:

        logger.debug("-*- Getting AwsResources")
        if self.aws_resource_group is None:
            self.init_resources()
            if self.aws_resource_group is None:
                print_info("No AwsResources available")
        return {}

    ######################################################
    ## Delete Resources
    ######################################################

    def delete_resources(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> bool:

        logger.debug("-*- Deleting AwsResources")
        if self.aws_resource_group is None:
            self.init_resources()
            if self.aws_resource_group is None:
                print_info("No AwsResources available")
                return False

        aws_resources_to_delete: Optional[
            List[AwsResourceType]
        ] = filter_and_flatten_aws_resource_group(
            aws_resource_group=self.aws_resource_group,
            name_filter=name_filter,
            type_filter=type_filter,
            sort_order="delete",
        )
        if aws_resources_to_delete is None or is_empty(aws_resources_to_delete):
            print_info("No AwsResources to delete")
            return True

        # track the total number of AwsResources to delete for validation
        num_resources_to_delete: int = len(aws_resources_to_delete)
        num_resources_deleted: int = 0

        # Print the resources for validation
        print_subheading(f"Deleting {num_resources_to_delete} AwsResources:")
        for rsrc in aws_resources_to_delete:
            print_info(f"  -+-> {rsrc.get_resource_type()}: {rsrc.get_resource_name()}")
        confirm = confirm_yes_no("\nConfirm delete")
        if not confirm:
            print_info("Skipping delete")
            return False

        for resource in aws_resources_to_delete:
            if resource:
                print_info(
                    f"\n-==+==- {resource.get_resource_type()}: {resource.get_resource_name()}"
                )
                # logger.debug(resource)
                try:
                    _resource_deleted = resource.delete(aws_client=self.aws_api_client)
                    if _resource_deleted:
                        num_resources_deleted += 1
                except Exception as e:
                    print_error(
                        f"-==+==--> Resource {resource.get_resource_type()}: {resource.get_resource_name()} could not be deleted."
                    )
                    print_error(e)
                    print_error("Skipping resource deletion, please delete manually...")

        print_info(
            f"\n# Resources deleted: {num_resources_deleted}/{num_resources_to_delete}"
        )
        if num_resources_to_delete == num_resources_deleted:
            return True

        print_error(
            f"Resources deleted: {num_resources_deleted} do not match Resources required: {num_resources_to_delete}"
        )
        return False

    def delete_resources_dry_run(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> None:

        env = self.aws_args.env
        print_subheading(
            "AwsResources{}".format(f" for env: {env}" if env is not None else "")
        )
        if self.aws_resource_group is None:
            self.init_resources()
            if self.aws_resource_group is None:
                print_info("No AwsResources available")
                return

        aws_resources_to_delete: Optional[
            List[AwsResourceType]
        ] = filter_and_flatten_aws_resource_group(
            aws_resource_group=self.aws_resource_group,
            name_filter=name_filter,
            type_filter=type_filter,
            sort_order="delete",
        )
        if aws_resources_to_delete is None or is_empty(aws_resources_to_delete):
            print_info("No AwsResources to delete")
            return

        num_resources_to_delete: int = len(aws_resources_to_delete)
        print_info(
            f"\n-*- Shutting down this AwsConfig will delete {num_resources_to_delete} resources:"
        )
        for resource in aws_resources_to_delete:
            print_info(
                f"-==+==- {resource.__class__.__name__}: {resource.get_resource_name()}"
            )

    ######################################################
    ## Patch Resources
    ######################################################

    def patch_resources(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> bool:

        logger.debug("-*- Deleting AwsResources")
        if self.aws_resource_group is None:
            self.init_resources()
            if self.aws_resource_group is None:
                print_info("No AwsResources available")
                return False

        aws_resources_to_patch: Optional[
            List[AwsResourceType]
        ] = filter_and_flatten_aws_resource_group(
            aws_resource_group=self.aws_resource_group,
            name_filter=name_filter,
            type_filter=type_filter,
            sort_order="create",
        )
        if aws_resources_to_patch is None or is_empty(aws_resources_to_patch):
            print_info("No AwsResources to patch")
            return True

        # track the total number of AwsResources to patch for validation
        num_resources_to_patch: int = len(aws_resources_to_patch)
        num_resources_patched: int = 0

        # Print the resources for validation
        print_subheading(f"Patching {num_resources_to_patch} AwsResources:")
        for rsrc in aws_resources_to_patch:
            print_info(f"  -+-> {rsrc.get_resource_type()}: {rsrc.get_resource_name()}")
        confirm = confirm_yes_no("\nConfirm patch")
        if not confirm:
            print_info("Skipping patch")
            return False

        for resource in aws_resources_to_patch:
            if resource:
                print_info(
                    f"\n-==+==- {resource.get_resource_type()}: {resource.get_resource_name()}"
                )
                # logger.debug(resource)
                try:
                    _resource_patched = resource.update(aws_client=self.aws_api_client)
                    if _resource_patched:
                        num_resources_patched += 1
                except Exception as e:
                    print_error(
                        f"-==+==--> Resource {resource.get_resource_type()}: {resource.get_resource_name()} could not be patched."
                    )
                    print_error(e)
                    print_error("Skipping resource, please patch manually...")

        print_info(
            f"\n# Resources patched: {num_resources_patched}/{num_resources_to_patch}"
        )
        if num_resources_to_patch == num_resources_patched:
            return True

        print_error(
            f"Resources patched: {num_resources_patched} do not match Resources required: {num_resources_to_patch}"
        )
        return False

    def patch_resources_dry_run(
        self,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> None:

        env = self.aws_args.env
        print_subheading(
            "AwsResources{}".format(f" for env: {env}" if env is not None else "")
        )
        if self.aws_resource_group is None:
            self.init_resources()
            if self.aws_resource_group is None:
                print_info("No AwsResources available")
                return

        aws_resources_to_patch: Optional[
            List[AwsResourceType]
        ] = filter_and_flatten_aws_resource_group(
            aws_resource_group=self.aws_resource_group,
            name_filter=name_filter,
            type_filter=type_filter,
            sort_order="create",
        )
        if aws_resources_to_patch is None or is_empty(aws_resources_to_patch):
            print_info("No AwsResources to patch")
            return

        num_resources_to_patch: int = len(aws_resources_to_patch)
        print_info(
            f"\n-*- Updating this AwsConfig will patch {num_resources_to_patch} resources:"
        )
        for resource in aws_resources_to_patch:
            print_info(
                f"-==+==- {resource.__class__.__name__}: {resource.get_resource_name()}"
            )

    ######################################################
    ## End
    ######################################################

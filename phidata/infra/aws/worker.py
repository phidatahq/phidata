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

        for resource_group in self.aws_args.resources:
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

        # A list of tuples with 3 parts
        #   1. Resource group name
        #   2. Resource group weight
        #   3. List of Resources in group after filters
        aws_resources_to_create: List[Tuple[str, int, List[AwsResource]]] = []
        for aws_rg_name, aws_rg in self.aws_resources.items():
            logger.debug(f"Processing: {aws_rg_name}")

            # skip disabled AwsResourceTypeGroups
            if not aws_rg.enabled:
                continue

            # skip groups not matching app_filter if provided
            if app_filter is not None:
                if app_filter.lower() not in aws_rg_name.lower():
                    logger.debug(f"Skipping {aws_rg_name}")
                    continue

            aws_resources_in_group = get_aws_resources_from_group(
                aws_resource_group=aws_rg,
                name_filter=name_filter,
                type_filter=type_filter,
            )
            if len(aws_resources_in_group) > 0:
                aws_resources_to_create.append(
                    (aws_rg_name, aws_rg.weight, aws_resources_in_group)
                )

        if len(aws_resources_to_create) == 0:
            print_subheading("No AwsResource to create")
            return True

        aws_resources_to_create_sorted: List[
            Tuple[str, int, List[AwsResource]]
        ] = sorted(
            aws_resources_to_create,
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
            ) in aws_resources_to_create_sorted:
                print_subheading(f"\n{group_number}. {group_name}")
                resource_number += len(resource_list)
                group_number += 1
                for resource in resource_list:
                    print_info(
                        f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}"
                    )
            if self.aws_args.aws_region:
                print_info(f"\nRegion: {self.aws_args.aws_region}")
            if self.aws_args.aws_profile:
                print_info(f"Profile: {self.aws_args.aws_profile}")
            print_info(f"\nTotal {resource_number} resources")
            confirm = confirm_yes_no("\nConfirm deploy")
            if not confirm:
                print_info("Skipping deploy")
                return False

        # track the total number of AwsResource to create for validation
        num_resources_to_create: int = 0
        num_resources_created: int = 0

        for (group_name, group_weight, resource_list) in aws_resources_to_create_sorted:
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
                            aws_client=self.aws_api_client
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
        logger.debug("-*- Creating AwsResources")
        if self.aws_resources is None:
            self.init_resources()
            if self.aws_resources is None:
                print_info("No resources available")
                return

        # A list of tuples with 3 parts
        #   1. Resource group name
        #   2. Resource group weight
        #   3. List of Resources in group after filters
        aws_resources_to_create: List[Tuple[str, int, List[AwsResource]]] = []
        for aws_rg_name, aws_rg in self.aws_resources.items():
            logger.debug(f"Processing: {aws_rg_name}")

            # skip disabled AwsResourceGroups
            if not aws_rg.enabled:
                continue

            # skip groups not matching app_filter if provided
            if app_filter is not None:
                if app_filter.lower() not in aws_rg_name.lower():
                    logger.debug(f"Skipping {aws_rg_name}")
                    continue

            aws_resources_in_group = get_aws_resources_from_group(
                aws_resource_group=aws_rg,
                name_filter=name_filter,
                type_filter=type_filter,
            )
            if len(aws_resources_in_group) > 0:
                aws_resources_to_create.append(
                    (aws_rg_name, aws_rg.weight, aws_resources_in_group)
                )

        if len(aws_resources_to_create) == 0:
            print_info("No AwsResources to create")
            return

        aws_resources_to_create_sorted: List[
            Tuple[str, int, List[AwsResource]]
        ] = sorted(
            aws_resources_to_create,
            key=lambda x: x[1],
        )

        group_number = 1
        num_resources_to_create: int = 0
        print_heading("--**-- Aws resources:")
        for (group_name, group_weight, resource_list) in aws_resources_to_create_sorted:
            print_subheading(f"\n{group_number}. {group_name}")
            num_resources_to_create += len(resource_list)
            group_number += 1
            for resource in resource_list:
                print_info(
                    f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}"
                )
        if self.aws_args.aws_region:
            print_info(f"\nRegion: {self.aws_args.aws_region}")
        if self.aws_args.aws_profile:
            print_info(f"Profile: {self.aws_args.aws_profile}")
        print_info(f"\nTotal {num_resources_to_create} resources")

    ######################################################
    ## Read Resources
    ######################################################

    def get_resource_groups(self) -> Optional[Dict[str, AwsResourceGroup]]:

        logger.debug("-*- Getting AwsResources")
        if self.aws_resources is None:
            self.init_resources()
            if self.aws_resources is None:
                print_info("No Resources available")
                return {}

        return self.aws_resources

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

        # A list of tuples with 3 parts
        #   1. Resource group name
        #   2. Resource group weight
        #   3. List of Resources in group after filters
        aws_resources_to_delete: List[Tuple[str, int, List[AwsResource]]] = []
        for aws_rg_name, aws_rg in self.aws_resources.items():
            logger.debug(f"Processing: {aws_rg_name}")

            # skip disabled AwsResourceGroups
            if not aws_rg.enabled:
                continue

            # skip groups not matching app_filter if provided
            if app_filter is not None:
                if app_filter.lower() not in aws_rg_name.lower():
                    logger.debug(f"Skipping {aws_rg_name}")
                    continue

            aws_resources_in_group = get_aws_resources_from_group(
                aws_resource_group=aws_rg,
                name_filter=name_filter,
                type_filter=type_filter,
            )
            if len(aws_resources_in_group) > 0:
                aws_resources_to_delete.append(
                    (aws_rg_name, aws_rg.weight, aws_resources_in_group)
                )

        if len(aws_resources_to_delete) == 0:
            print_subheading("No AwsResources to delete")
            return True

        aws_resources_to_delete_sorted: List[
            Tuple[str, int, List[AwsResource]]
        ] = sorted(
            aws_resources_to_delete,
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
            ) in aws_resources_to_delete_sorted:
                print_subheading(f"\n{group_number}. {group_name}")
                resource_number += len(resource_list)
                group_number += 1
                for resource in resource_list:
                    print_info(
                        f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}"
                    )
            if self.aws_args.aws_region:
                print_info(f"\nRegion: {self.aws_args.aws_region}")
            if self.aws_args.aws_profile:
                print_info(f"Profile: {self.aws_args.aws_profile}")
            print_info(f"\nTotal {resource_number} resources")
            confirm = confirm_yes_no("\nConfirm delete")
            if not confirm:
                print_info("Skipping delete")
                return False

        # track the total number of AwsResources to create for validation
        num_resources_to_delete: int = 0
        num_resources_deleted: int = 0

        for (group_name, group_weight, resource_list) in aws_resources_to_delete_sorted:
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
                            aws_client=self.aws_api_client
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
        logger.debug("-*- Deleting AwsResources")
        if self.aws_resources is None:
            self.init_resources()
            if self.aws_resources is None:
                print_info("No resources available")
                return

        # A list of tuples with 3 parts
        #   1. Resource group name
        #   2. Resource group weight
        #   3. List of Resources in group after filters
        aws_resources_to_delete: List[Tuple[str, int, List[AwsResource]]] = []
        for aws_rg_name, aws_rg in self.aws_resources.items():
            logger.debug(f"Processing: {aws_rg_name}")

            # skip disabled AwsResourceGroups
            if not aws_rg.enabled:
                continue

            # skip groups not matching app_filter if provided
            if app_filter is not None:
                if app_filter.lower() not in aws_rg_name.lower():
                    logger.debug(f"Skipping {aws_rg_name}")
                    continue

            aws_resources_in_group = get_aws_resources_from_group(
                aws_resource_group=aws_rg,
                name_filter=name_filter,
                type_filter=type_filter,
            )
            if len(aws_resources_in_group) > 0:
                aws_resources_to_delete.append(
                    (aws_rg_name, aws_rg.weight, aws_resources_in_group)
                )

        if len(aws_resources_to_delete) == 0:
            print_info("No AwsResources to create")
            return

        aws_resources_to_delete_sorted: List[
            Tuple[str, int, List[AwsResource]]
        ] = sorted(
            aws_resources_to_delete,
            key=lambda x: x[1],
            reverse=True,
        )

        group_number = 1
        num_resources_to_delete: int = 0
        print_heading("--**-- Aws resources:")
        for (group_name, group_weight, resource_list) in aws_resources_to_delete_sorted:
            print_subheading(f"\n{group_number}. {group_name}")
            num_resources_to_delete += len(resource_list)
            group_number += 1
            for resource in resource_list:
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

        # A list of tuples with 3 parts
        #   1. Resource group name
        #   2. Resource group weight
        #   3. List of Resources in group after filters
        aws_resources_to_patch: List[Tuple[str, int, List[AwsResource]]] = []
        for aws_rg_name, aws_rg in self.aws_resources.items():
            logger.debug(f"Processing: {aws_rg_name}")

            # skip disabled AwsResourceGroups
            if not aws_rg.enabled:
                continue

            # skip groups not matching app_filter if provided
            if app_filter is not None:
                if app_filter.lower() not in aws_rg_name.lower():
                    logger.debug(f"Skipping {aws_rg_name}")
                    continue

            aws_resources_in_group = get_aws_resources_from_group(
                aws_resource_group=aws_rg,
                name_filter=name_filter,
                type_filter=type_filter,
            )
            if len(aws_resources_in_group) > 0:
                aws_resources_to_patch.append(
                    (aws_rg_name, aws_rg.weight, aws_resources_in_group)
                )

        if len(aws_resources_to_patch) == 0:
            print_subheading("No AwsResources to patch")
            return True

        aws_resources_to_patch_sorted: List[
            Tuple[str, int, List[AwsResource]]
        ] = sorted(
            aws_resources_to_patch,
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
            ) in aws_resources_to_patch_sorted:
                print_subheading(f"\n{group_number}. {group_name}")
                resource_number += len(resource_list)
                group_number += 1
                for resource in resource_list:
                    print_info(
                        f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}"
                    )
            if self.aws_args.aws_region:
                print_info(f"\nRegion: {self.aws_args.aws_region}")
            if self.aws_args.aws_profile:
                print_info(f"Profile: {self.aws_args.aws_profile}")
            print_info(f"\nTotal {resource_number} resources")
            confirm = confirm_yes_no("\nConfirm patch")
            if not confirm:
                print_info("Skipping patch")
                return False

        # track the total number of AwsResources to patch for validation
        num_resources_to_patch: int = 0
        num_resources_patched: int = 0

        for (group_name, group_weight, resource_list) in aws_resources_to_patch_sorted:
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
                            aws_client=self.aws_api_client
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
        logger.debug("-*- Patching AwsResources")
        if self.aws_resources is None:
            self.init_resources()
            if self.aws_resources is None:
                print_info("No resources available")
                return

        # A list of tuples with 3 parts
        #   1. Resource group name
        #   2. Resource group weight
        #   3. List of Resources in group after filters
        aws_resources_to_patch: List[Tuple[str, int, List[AwsResource]]] = []
        for aws_rg_name, aws_rg in self.aws_resources.items():
            logger.debug(f"Processing: {aws_rg_name}")

            # skip disabled AwsResourceGroups
            if not aws_rg.enabled:
                continue

            # skip groups not matching app_filter if provided
            if app_filter is not None:
                if app_filter.lower() not in aws_rg_name.lower():
                    logger.debug(f"Skipping {aws_rg_name}")
                    continue

            aws_resources_in_group = get_aws_resources_from_group(
                aws_resource_group=aws_rg,
                name_filter=name_filter,
                type_filter=type_filter,
            )
            if len(aws_resources_in_group) > 0:
                aws_resources_to_patch.append(
                    (aws_rg_name, aws_rg.weight, aws_resources_in_group)
                )

        if len(aws_resources_to_patch) == 0:
            print_info("No AwsResources to patch")
            return

        aws_resources_to_patch_sorted: List[
            Tuple[str, int, List[AwsResource]]
        ] = sorted(
            aws_resources_to_patch,
            key=lambda x: x[1],
        )

        group_number = 1
        num_resources_to_patch: int = 0
        print_heading("--**-- Aws resources:")
        for (group_name, group_weight, resource_list) in aws_resources_to_patch_sorted:
            print_subheading(f"\n{group_number}. {group_name}")
            num_resources_to_patch += len(resource_list)
            group_number += 1
            for resource in resource_list:
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

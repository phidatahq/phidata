from typing import List, Optional, Type, Tuple, Set

from typing_extensions import Literal

from phidata.infra.aws.resource.base import AwsResource
from phidata.infra.aws.resource.group import AwsResourceGroup
from phidata.infra.aws.resource.types import (
    AwsResourceInstallOrder,
    AwsResourceType,
)
from phidata.utils.log import logger


def get_install_weight_for_aws_resource(aws_resource_type: AwsResourceType) -> int:
    """Function which returns the install weight for an AwsResource"""

    resource_type_class_name = aws_resource_type.__class__.__name__
    if resource_type_class_name in AwsResourceInstallOrder.keys():
        install_weight = AwsResourceInstallOrder[resource_type_class_name]
        # logger.debug(
        #     "Resource type: {} | Install weight: {}".format(
        #         resource_type_class_name,
        #         install_weight,
        #     )
        # )
        return install_weight
    return 1000


def filter_aws_resources_group(
    aws_resource_group: AwsResourceGroup,
    name_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
) -> Optional[List[AwsResourceType]]:
    """Filters the AwsResourceGroup using name_filter and type_filter.
    This function also flattens any List[AwsResourceType] attributes.
    Eg: it will flatten s3_buckets

    Args:
        aws_resource_group:
        name_filter:
        type_filter:

    Returns:
        Optional[List[AwsResourceType]]: List of filtered and flattened Aws Resources
    """

    # List of all resources in this AwsResourceGroup
    all_resources: List = []
    # List of filtered resources
    filtered_resources: List = []
    logger.debug(f"Filtering AwsResourceGroup {aws_resource_group.name}")

    # Populate all_resources list
    for resource, resource_data in aws_resource_group.__dict__.items():
        # logger.debug("resource: {}".format(resource))

        ## Check if the resource is a single AwsResourceType or a List[AwsResourceType]

        # If the resource is a List[AwsResourceType], flatten the resources, verify each element
        # is isinstance of AwsResource and add to the all_resources list
        if isinstance(resource_data, list):
            for _r in resource_data:
                if isinstance(_r, AwsResource):
                    all_resources.append(_r)
        # If the resource is a single resource, verify that the resource isinstance of
        # AwsResource and add it to the all_resources list
        elif isinstance(resource_data, AwsResource):
            all_resources.append(resource_data)

    # Apply filters
    if name_filter is not None or type_filter is not None:
        for resource in all_resources:
            if not isinstance(resource, AwsResource):
                continue
            resource_name = resource.get_resource_name()
            resource_type = resource.get_resource_type()
            # skip resources that dont match the name_filter
            if name_filter is not None:
                if resource_name is None:
                    logger.debug(f"Skipping unnamed resource, type: {resource_type}")
                    continue
                if name_filter.lower() not in resource_name.lower():
                    logger.debug(f"Skipping {resource_type} | {resource_name}")
                    continue
            # skip resources that dont match the type_filter
            if type_filter is not None:
                resource_type = resource.get_resource_type()
                if resource_type is None:
                    logger.debug(f"Skipping untyped resource, name: {resource_name}")
                    continue
                if type_filter.lower() not in resource_type.lower():
                    logger.debug(f"Skipping {resource_type} | {resource_name}")
                    continue
            filtered_resources.append(resource)
    else:
        filtered_resources = all_resources

    return filtered_resources


# def dedup_resource_types(
#     aws_resources: Optional[List[AwsResourceType]] = None,
# ) -> Optional[Set[Type[AwsResource]]]:
#     """Takes a list of AwsResources and returns a Set of AwsResource classes.
#     Each AwsResource classes is represented by the Type[resources.AwsResource] type.
#     From python docs:
#         A variable annotated with Type[AwsResource] may accept values that are classes.
#         Acceptable classes are the AwsResource class + subclasses.
#     """
#     if aws_resources:
#         active_resource_types: Set[Type[AwsResource]] = set()
#         for resource in aws_resources:
#             active_resource_types.add(resource.__class__)
#             # logger.debug(f"Gathering: {resource.get_resource_name()}")
#             # logger.debug(f"Resource Type: {resource_type}")
#         logger.debug("Active Resource Types: {}".format(active_resource_types))
#         return active_resource_types
#     return None


def filter_and_flatten_aws_resource_group(
    aws_resource_group: AwsResourceGroup,
    name_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
    sort_order: Literal["create", "delete"] = "create",
) -> Optional[List[AwsResourceType]]:
    """This function flattens the aws_resource_group and returns a filtered list of
    AwsResources sorted in the order requested. create == install order, delete == reverse

    Args:
        aws_resource_group: AwsResourceGroup
        name_filter: Filter AwsResources by name
        type_filter: Filter AwsResources by type
        sort_order: create or delete

    Returns:
        List[AwsResourceType]: List of filtered Aws Resources
    """

    filtered_aws_resources: Optional[List[AwsResourceType]] = None
    if aws_resource_group is not None and aws_resource_group.enabled:
        # logger.debug(f"Flattening AwsResourceGroup {aws_resource_group.name}")
        filtered_aws_resources = filter_aws_resources_group(
            aws_resource_group, name_filter, type_filter
        )
    if filtered_aws_resources is None:
        return None

    # Sort the resources in install order
    if sort_order == "create":
        filtered_aws_resources.sort(
            key=lambda x: get_install_weight_for_aws_resource(x)
        )
    elif sort_order == "delete":
        filtered_aws_resources.sort(
            key=lambda x: get_install_weight_for_aws_resource(x), reverse=True
        )

    # logger.debug("filtered_aws_resources: {}".format(filtered_aws_resources))
    return filtered_aws_resources

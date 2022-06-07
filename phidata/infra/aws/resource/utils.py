from typing import List, Optional, Dict, Tuple

from typing_extensions import Literal

from phidata.infra.aws.resource.base import AwsResource
from phidata.infra.aws.resource.group import AwsResourceGroup
from phidata.infra.aws.resource.types import (
    AwsResourceInstallOrder,
    AwsResourceType,
)
from phidata.utils.log import logger


def get_install_weight_for_aws_resource(
    aws_resource_type: AwsResource, resource_group_weight: int = 100
) -> int:
    """Function which returns the install weight for an AwsResource"""

    resource_type_class_name = aws_resource_type.__class__.__name__
    if resource_type_class_name in AwsResourceInstallOrder.keys():
        install_weight = AwsResourceInstallOrder[resource_type_class_name]
        final_weight = resource_group_weight * install_weight
        # logger.debug(
        #     "Resource type: {} | Install weight: {}".format(
        #         resource_type_class_name,
        #         install_weight,
        #     )
        # )
        return final_weight

    return 5000


def get_aws_resources_from_group(
    aws_resource_group: AwsResourceGroup,
    name_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
) -> List[AwsResource]:
    """Parses the AwsResourceGroup and returns an array of AwsResources
    after applying the name & type filters. This function also flattens any
    List[AwsResource] attributes. Eg: it will flatten s3_buckets

    Args:
        aws_resource_group:
        name_filter: filter AwsResources by name
        type_filter: filter AwsResources by type

    Returns:
        List[AwsResource]: List of filtered and flattened Aws Resources
    """

    # List of resources to return
    aws_resources: List[AwsResource] = []
    # logger.debug(f"Flattening {aws_resource_group.name}")

    # populate the aws_resources list with the resources
    # Loop over each key of the AwsResourceGroup model
    for resource, resource_data in aws_resource_group.__dict__.items():
        # logger.debug("resource: {}".format(resource))
        # logger.debug("resource_data: {}".format(resource_data))

        # Check if the resource is a single AwsResource or a List[AwsResource]
        # If it is a List[AwsResource], flatten the resources, verify each element
        # of the list is a subclass of AwsResource and add to the aws_resources list
        if isinstance(resource_data, list):
            for _r in resource_data:
                if isinstance(_r, AwsResource):
                    rn = _r.get_resource_name()
                    rt = _r.get_resource_type()
                    if name_filter is not None and rn is not None:
                        # logger.debug(f"name_filter: {name_filter.lower()}")
                        # logger.debug(f"resource name: {rn.lower()}")
                        if name_filter.lower() not in rn.lower():
                            logger.debug(f"  -*- skipping {rt}:{rn}")
                            continue

                    if type_filter is not None and rt is not None:
                        # logger.debug(f"type_filter: {type_filter.lower()}")
                        # logger.debug(f"class: {rt.lower()}")
                        if type_filter.lower() != rt.lower():
                            logger.debug(f"  -*- skipping {rt}:{rn}")
                            continue
                    aws_resources.append(_r)  # type: ignore

        # If its a single resource, verify that the resource is a subclass of
        # AwsResource and add it to the aws_resources list
        elif isinstance(resource_data, AwsResource):
            rn = resource_data.get_resource_name()
            rt = resource_data.get_resource_type()
            if name_filter is not None and rn is not None:
                # logger.debug(f"name_filter: {name_filter.lower()}")
                # logger.debug(f"resource name: {rn.lower()}")
                if name_filter.lower() not in rn.lower():
                    # logger.debug(f"skipping {rt}:{rn}")
                    continue

            if type_filter is not None and rt is not None:
                # logger.debug(f"type_filter: {type_filter.lower()}")
                # logger.debug(f"class: {rt.lower()}")
                if type_filter.lower() != rt.lower():
                    # logger.debug(f"skipping {rt}:{rn}")
                    continue
            aws_resources.append(resource_data)  # type: ignore

    return aws_resources


# def dedup_resource_types(
#     aws_resources: Optional[List[AwsResource]] = None,
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


def dedup_aws_resources(
    aws_resources_with_weight: List[Tuple[AwsResource, int]],
) -> List[Tuple[AwsResource, int]]:
    if aws_resources_with_weight is None:
        raise ValueError

    deduped_resources: List[Tuple[AwsResource, int]] = []
    prev_rsrc: Optional[AwsResource] = None
    prev_weight: Optional[int] = None
    for rsrc, weight in aws_resources_with_weight:
        # First item of loop
        if prev_rsrc is None:
            prev_rsrc = rsrc
            prev_weight = weight
            deduped_resources.append((rsrc, weight))
            continue

        # Compare resources with same weight only
        if weight == prev_weight:
            if (
                rsrc.get_resource_type() == prev_rsrc.get_resource_type()
                and rsrc.get_resource_name() == prev_rsrc.get_resource_name()
                and rsrc.get_resource_name() is not None
            ):
                # If resource type and name are the same, skip the resource
                # Note: resource.name cannot be None
                continue

        # If the loop hasn't been continued by the if blocks above,
        # add the resource and weight to the deduped_resources list
        deduped_resources.append((rsrc, weight))
        # update the previous resource for comparison
        prev_rsrc = rsrc
        prev_weight = weight
    return deduped_resources


def filter_and_flatten_aws_resource_groups(
    aws_resource_groups: Dict[str, AwsResourceGroup],
    name_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
    app_filter: Optional[str] = None,
    sort_order: Literal["create", "delete"] = "create",
) -> List[AwsResource]:
    """This function flattens the aws_resource_group and returns a filtered list of
    AwsResources sorted in the order requested. create == install order, delete == reverse

    Args:
        aws_resource_groups: AwsResourceGroup
        name_filter: Filter AwsResources by name
        type_filter: Filter AwsResources by type
        app_filter: Filter AwsResources by aws resource group name
        sort_order: create or delete

    Returns:
        List[AwsResource]: List of filtered Aws Resources
    """

    logger.debug("Filtering & Flattening AwsResourceGroups")

    # Step 1: Create aws_resource_list_with_weight
    # A List of Tuples where each tuple is a (AwsResource, Resource Group Weight)
    # The reason for creating this list is so that we can sort the AwsResources
    # based on their resource group weight using get_install_weight_for_aws_resource
    aws_resource_list_with_weight: List[Tuple[AwsResource, int]] = []
    if aws_resource_groups:
        # Iterate through aws_resource_groups
        for aws_rg_name, aws_rg in aws_resource_groups.items():
            # logger.debug("aws_rg_name: {}".format(aws_rg_name))
            # logger.debug("aws_rg: {}".format(aws_rg))

            # skip disabled AwsResourceGroups
            if not aws_rg.enabled:
                continue

            # skip groups not matching app_filter if provided
            if app_filter is not None and aws_rg_name is not None:
                # logger.debug(f"matching app_filter: {app_filter}")
                # logger.debug(f"with aws_rg_name: {aws_rg_name}")
                if app_filter.lower() not in aws_rg_name.lower():
                    logger.debug(f"  -*- skipping {aws_rg_name}")
                    continue

            aws_resources = get_aws_resources_from_group(
                aws_rg, name_filter, type_filter
            )
            if aws_resources:
                for _aws_rsrc in aws_resources:
                    aws_resource_list_with_weight.append((_aws_rsrc, aws_rg.weight))

    # Sort the resources in install order
    if sort_order == "create":
        aws_resource_list_with_weight.sort(
            key=lambda x: get_install_weight_for_aws_resource(x[0], x[1])
        )
    elif sort_order == "delete":
        aws_resource_list_with_weight.sort(
            key=lambda x: get_install_weight_for_aws_resource(x[0], x[1]), reverse=True
        )

    # De-duplicate AwsResources
    deduped_aws_resources: List[Tuple[AwsResource, int]] = dedup_aws_resources(
        aws_resource_list_with_weight
    )
    # deduped_aws_resources = aws_resource_list_with_weight
    # logger.debug("AwsResource list")
    # logger.debug(
    #     "\n".join(
    #         "Name: {}, Type: {}, Weight: {}".format(
    #             rsrc.name, rsrc.resource_type, weight
    #         )
    #         for rsrc, weight in deduped_aws_resources
    #     )
    # )

    # drop the weight from the deduped_aws_resources tuple
    filtered_aws_resources: List[AwsResource] = [x[0] for x in deduped_aws_resources]
    # logger.debug("filtered_aws_resources: {}".format(filtered_aws_resources))
    return filtered_aws_resources

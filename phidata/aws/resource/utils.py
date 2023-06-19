from typing import List, Optional, Dict, Tuple, Set

from typing_extensions import Literal

from phidata.aws.resource.base import AwsResource
from phidata.aws.resource.group import AwsResourceGroup
from phidata.aws.resource.types import AwsResourceInstallOrder
from phidata.utils.log import logger


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
                    # skip disabled resources
                    if not _r.enabled:
                        logger.debug(f"  -*- skipping {rt}:{rn}")
                        continue

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
            # skip disabled resources
            if not resource_data.enabled:
                logger.debug(f"  -*- skipping {rt}:{rn}")
                continue

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


def get_rank_for_aws_resource(aws_resource_type: AwsResource) -> int:
    """Function which returns the install rank for an AwsResource"""

    resource_type_class_name = aws_resource_type.__class__.__name__
    if resource_type_class_name in AwsResourceInstallOrder.keys():
        install_rank = AwsResourceInstallOrder[resource_type_class_name]
        return install_rank

    return 5000


def dedup_aws_resources(aws_resource_list: List[AwsResource]) -> List[AwsResource]:
    deduped_resources: List[AwsResource] = []
    for rsrc in aws_resource_list:
        if rsrc not in deduped_resources:
            deduped_resources.append(rsrc)
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

    # Step 1: Create a lit of aws_resources
    aws_resource_list: List[AwsResource] = []
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

            _aws_resources = get_aws_resources_from_group(
                aws_rg, name_filter, type_filter
            )
            if _aws_resources:
                aws_resource_list.extend(_aws_resources)

    # Sort the resources in install order
    if sort_order == "create":
        aws_resource_list.sort(key=lambda x: get_rank_for_aws_resource(x))
    elif sort_order == "delete":
        aws_resource_list.sort(key=lambda x: get_rank_for_aws_resource(x), reverse=True)

    # De-duplicate AwsResources
    deduped_aws_resources: List[AwsResource] = dedup_aws_resources(aws_resource_list)

    # Implement dependency sorting
    final_aws_resources: List[AwsResource] = []
    for aws_resource in deduped_aws_resources:
        # Logic to follow if resource has dependencies
        if aws_resource.depends_on is not None:
            # If the sort_order is delete
            # 1. Reverse the order of dependencies
            # 2. Remove the dependencies if they are already added to the final_aws_resources
            # 3. Add the resource to be deleted before its dependencies
            # 4. Add the dependencies back in reverse order
            if sort_order == "delete":
                # 1. Reverse the order of dependencies
                aws_resource.depends_on.reverse()
                # 2. Remove the dependencies if they are already added to the final_aws_resources
                for dep in aws_resource.depends_on:
                    if dep in final_aws_resources:
                        logger.debug(
                            f"  -*- Removing {dep.name}, dependency of {aws_resource.name}"
                        )
                        final_aws_resources.remove(dep)
                # 3. Add the resource to be deleted before its dependencies
                if aws_resource not in final_aws_resources:
                    logger.debug(f"  -*- Adding {aws_resource.name}")
                    final_aws_resources.append(aws_resource)

            # Common logic for create and delete
            # When the sort_order is create, the dependencies are added before the resource
            # When the sort_order is delete, the dependencies are added after the resource
            for dep in aws_resource.depends_on:
                if isinstance(dep, AwsResource):
                    if dep not in final_aws_resources:
                        logger.debug(
                            f"  -*- Adding {dep.name}, dependency of {aws_resource.name}"
                        )
                        final_aws_resources.append(dep)

            # If the sort_order is create,
            # add the resource to be created after its dependencies
            if sort_order == "create":
                if aws_resource not in final_aws_resources:
                    logger.debug(f"  -*- Adding {aws_resource.name}")
                    final_aws_resources.append(aws_resource)
        else:
            # Add the resource to be created/deleted
            if aws_resource not in final_aws_resources:
                logger.debug(f"  -*- Adding {aws_resource.name}")
                final_aws_resources.append(aws_resource)

    return final_aws_resources

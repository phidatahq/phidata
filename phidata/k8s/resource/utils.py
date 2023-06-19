from typing import Dict, List, Optional, Type, Tuple, Set

from typing_extensions import Literal

from phidata.k8s.resource.base import K8sResource
from phidata.k8s.resource.group import K8sResourceGroup
from phidata.k8s.resource.types import K8sResourceInstallOrder
from phidata.utils.log import logger


def get_k8s_resources_from_group(
    k8s_resource_group: K8sResourceGroup,
    name_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
    sort_order: Literal["create", "delete"] = "create",
) -> List[K8sResource]:
    """Parses the K8sResourceGroup and returns an array of K8sResources
    after applying the name & type filters. This function also flattens any
    List[K8sResource] attributes. Eg: it will flatten pvc, cm, secret and
    storage_class resources.

    Args:
        k8s_resource_group:
        name_filter: filter K8sResources by name
        type_filter: filter K8sResources by type
        sort_order: create or delete

    Returns:
        List[K8sResource]: List of filtered and flattened K8s Resources
    """

    # List of resources to return
    k8s_resources: List[K8sResource] = []
    # logger.debug(f"Flattening {k8s_resource_group.name}")

    # populate the k8s_resources list with the resources
    # Loop over each key of the K8sResourceGroup model
    for resource, resource_data in k8s_resource_group.__dict__.items():
        # logger.debug("resource: {}".format(resource))
        # logger.debug("resource_data: {}".format(resource_data))

        # Check if the resource is a single K8sResource or a List[K8sResource]
        # If it is a List[K8sResource], flatten the resources, verify each element
        # of the list is a subclass of K8sResource and add to the k8s_resources list
        if isinstance(resource_data, list):
            for _r in resource_data:
                if isinstance(_r, K8sResource):
                    rn = _r.get_resource_name()
                    rt = _r.get_resource_type()
                    # skip disabled resources
                    if not _r.enabled:
                        logger.debug(f"  -*- skipping {rt}:{rn}")
                        continue

                    if name_filter is not None and rn is not None:
                        logger.debug(f"name_filter: {name_filter.lower()}")
                        # logger.debug(f"resource name: {rn.lower()}")
                        if name_filter.lower() not in rn.lower():
                            logger.debug(f"  -*- skipping {rt}:{rn}")
                            continue

                    if type_filter is not None and rt is not None:
                        logger.debug(f"type_filter: {type_filter.lower()}")
                        # logger.debug(f"class: {rt.lower()}")
                        if type_filter.lower() != rt.lower():
                            logger.debug(f"  -*- skipping {rt}:{rn}")
                            continue
                    k8s_resources.append(_r)  # type: ignore

        # If its a single resource, verify that the resource is a subclass of
        # K8sResource and add it to the k8s_resources list
        elif isinstance(resource_data, K8sResource):
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
            k8s_resources.append(resource_data)  # type: ignore

    return k8s_resources


def get_rank_for_k8s_resource(k8s_resource_type: K8sResource) -> int:
    """Function which returns the install rank for a K8sResource"""

    resource_type_class_name = k8s_resource_type.__class__.__name__
    if resource_type_class_name in K8sResourceInstallOrder.keys():
        install_rank = K8sResourceInstallOrder[resource_type_class_name]
        return install_rank

    return 5000


def dedup_k8s_resources(k8s_resource_list: List[K8sResource]) -> List[K8sResource]:
    deduped_resources: List[K8sResource] = []
    for rsrc in k8s_resource_list:
        if rsrc not in deduped_resources:
            deduped_resources.append(rsrc)
    return deduped_resources


def filter_and_flatten_k8s_resource_groups(
    k8s_resource_groups: Dict[str, K8sResourceGroup],
    name_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
    app_filter: Optional[str] = None,
    sort_order: Literal["create", "delete"] = "create",
) -> Optional[List[K8sResource]]:
    """This function parses the k8s_resource_groups dict and returns a filtered array of
    K8sResources sorted in the order requested. create == install order, delete == reverse
    Desc:
        1. Iterate through each K8sResourceGroup
        2. If enabled, get the K8s Resources from that group which match the filters
        2. Return a list of all K8sResources from 2.

    Args:
        k8s_resource_groups: Dict[str, resources.K8sResourceGroup]
            Dict of {resource_group_name : K8sResourceGroup}
        name_filter: Filter K8sResourceGroup by name
        type_filter: Filter K8sResourceGroup by type
        app_filter: Filter K8sResourceGroup by app
        sort_order: create or delete

    Returns:
        List[K8sResource]: List of filtered K8s Resources
    """

    logger.debug("Filtering & Flattening K8sResourceGroups")

    # Step 1: Create a list of k8s_resources
    k8s_resource_list: List[K8sResource] = []
    if k8s_resource_groups:
        # Iterate through k8s_resource_groups
        for k8s_rg_name, k8s_rg in k8s_resource_groups.items():
            # logger.debug("k8s_rg_name: {}".format(k8s_rg_name))
            # logger.debug("k8s_rg: {}".format(k8s_rg))

            # skip disabled K8sResourceGroups
            if not k8s_rg.enabled:
                continue

            # skip groups not matching app_filter if provided
            if app_filter is not None and k8s_rg_name is not None:
                # logger.debug(f"matching app_filter: {app_filter}")
                # logger.debug(f"with k8s_rg_name: {k8s_rg_name}")
                if app_filter.lower() not in k8s_rg_name.lower():
                    logger.debug(f"  -*- skipping {k8s_rg_name}")
                    continue

            _k8s_resources = get_k8s_resources_from_group(
                k8s_rg, name_filter, type_filter
            )
            if _k8s_resources:
                k8s_resource_list.extend(_k8s_resources)

    # Sort the resources in install order
    if sort_order == "create":
        k8s_resource_list.sort(key=lambda x: get_rank_for_k8s_resource(x))
    elif sort_order == "delete":
        k8s_resource_list.sort(key=lambda x: get_rank_for_k8s_resource(x), reverse=True)

    # De-duplicate K8sResources
    deduped_k8s_resources: List[K8sResource] = dedup_k8s_resources(k8s_resource_list)

    # Implement dependency sorting and drop the weight
    final_k8s_resources: List[K8sResource] = []
    for k8s_resource in deduped_k8s_resources:
        # Logic to follow if resource has dependencies
        if k8s_resource.depends_on is not None:
            # If the sort_order is delete
            # 1. Reverse the order of dependencies
            # 2. Remove the dependencies if they are already added to the final_k8s_resources
            # 3. Add the resource to be deleted before its dependencies
            # 4. Add the dependencies back in reverse order
            if sort_order == "delete":
                # 1. Reverse the order of dependencies
                k8s_resource.depends_on.reverse()
                # 2. Remove the dependencies if they are already added to the final_k8s_resources
                for dep in k8s_resource.depends_on:
                    if dep in final_k8s_resources:
                        logger.debug(
                            f"  -*- Removing {dep.name}, dependency of {k8s_resource.name}"
                        )
                        final_k8s_resources.remove(dep)
                # 3. Add the resource to be deleted before its dependencies
                if k8s_resource not in final_k8s_resources:
                    logger.debug(f"  -*- Adding {k8s_resource.name}")
                    final_k8s_resources.append(k8s_resource)

            # Common logic for create and delete
            # When the sort_order is create, the dependencies are added before the resource
            # When the sort_order is delete, the dependencies are added after the resource
            for dep in k8s_resource.depends_on:
                if isinstance(dep, K8sResource):
                    if dep not in final_k8s_resources:
                        logger.debug(
                            f"  -*- Adding {dep.name}, dependency of {k8s_resource.name}"
                        )
                        final_k8s_resources.append(dep)

            # If the sort_order is create,
            # add the resource to be created after its dependencies
            if sort_order == "create":
                if k8s_resource not in final_k8s_resources:
                    logger.debug(f"  -*- Adding {k8s_resource.name}")
                    final_k8s_resources.append(k8s_resource)
        else:
            # Add the resource to be created/deleted
            if k8s_resource not in final_k8s_resources:
                logger.debug(f"  -*- Adding {k8s_resource.name}")
                final_k8s_resources.append(k8s_resource)

    return final_k8s_resources

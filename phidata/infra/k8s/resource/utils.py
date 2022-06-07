from typing import Dict, List, Optional, Type, Tuple, Set

from typing_extensions import Literal

from phidata.infra.k8s.resource.base import K8sResource
from phidata.infra.k8s.resource.group import K8sResourceGroup
from phidata.infra.k8s.resource.types import K8sResourceInstallOrder
from phidata.utils.log import logger


def get_install_weight_for_k8s_resource(
    k8s_resource_type: K8sResource, resource_group_weight: int = 100
) -> int:
    """Function which takes a K8sResource and resource_group_weight and returns the install
    weight for that resource.

    Understanding install weights for K8s Resources:

    - Each K8sResource gets an install weight, which determines the order for installing that particular resource.
    - By default, K8sResources are installed in the order determined by the K8sResourceInstallOrder dict.
        The K8sResourceInstallOrder dict ensures namespaces/service accounts are applied before deployments
    - We can also provide a weight to the K8sResourceGroup, that weight determines the install order for all resources within
        that resource group as compared to other resource groups.
    - We achieve this by multiplying the K8sResourceGroup.weight with the value from K8sResourceInstallOrder
        and by default using a weight of 100. So
        * Weights 1-10 are reserved
        * Choose weight 11-99 to deploy a resource group before all the "default" resources
        * Choose weight 101+ to deploy a resource group after all the "default" resources
        * Choosing weight 100 has no effect because that is the default install weight
    """
    resource_type_class_name = k8s_resource_type.__class__.__name__
    if resource_type_class_name in K8sResourceInstallOrder.keys():
        install_weight = K8sResourceInstallOrder[resource_type_class_name]
        final_weight = resource_group_weight * install_weight
        # logger.debug(
        #     "Resource type: {} | RG Weight: {} | Install weight: {} | Final weight: {}".format(
        #         resource_type_class_name,
        #         resource_group_weight,
        #         install_weight,
        #         final_weight,
        #     )
        # )
        return final_weight

    return 5000


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

    # Sort the resources in install order
    if sort_order == "create":
        k8s_resources.sort(
            key=lambda x: get_install_weight_for_k8s_resource(
                x, k8s_resource_group.weight
            )
        )
    elif sort_order == "delete":
        k8s_resources.sort(
            key=lambda x: get_install_weight_for_k8s_resource(
                x, k8s_resource_group.weight
            ),
            reverse=True,
        )
    return k8s_resources


def dedup_resource_types(
    k8s_resources: Optional[List[K8sResource]] = None,
) -> Optional[Set[Type[K8sResource]]]:
    """Takes a list of K8sResources and returns a Set of K8sResource classes.
    Each K8sResource classes is represented by the Type[resources.K8sResource] type.
    From python docs:
        A variable annotated with Type[K8sResource] may accept values that are classes.
        Acceptable classes are the K8sResource class + subclasses.
    """
    if k8s_resources:
        active_resource_types: Set[Type[K8sResource]] = set()
        for resource in k8s_resources:
            active_resource_types.add(resource.__class__)
            # logger.debug(f"Gathering: {resource.get_resource_name()}")
            # logger.debug(f"Resource Type: {resource_type}")
        logger.debug("Active Resource Types: {}".format(active_resource_types))
        return active_resource_types
    return None


def dedup_k8s_resources(
    k8s_resources_with_weight: List[Tuple[K8sResource, int]],
) -> List[Tuple[K8sResource, int]]:
    if k8s_resources_with_weight is None:
        raise ValueError

    deduped_resources: List[Tuple[K8sResource, int]] = []
    prev_rsrc: Optional[K8sResource] = None
    prev_weight: Optional[int] = None
    for rsrc, weight in k8s_resources_with_weight:
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

    # Step 1: Create k8s_resource_list_with_weight
    # A List of Tuples where each tuple is a (K8sResource, Resource Group Weight)
    # The reason for creating this list is so that we can sort the K8sResources
    # based on their resource group weight using get_install_weight_for_k8s_resource
    k8s_resource_list_with_weight: List[Tuple[K8sResource, int]] = []
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

            k8s_resources = get_k8s_resources_from_group(
                k8s_rg, name_filter, type_filter
            )
            if k8s_resources:
                for _k8s_rsrc in k8s_resources:
                    k8s_resource_list_with_weight.append((_k8s_rsrc, k8s_rg.weight))

    # Sort the resources in install order
    if sort_order == "create":
        k8s_resource_list_with_weight.sort(
            key=lambda x: get_install_weight_for_k8s_resource(x[0], x[1])
        )
    elif sort_order == "delete":
        k8s_resource_list_with_weight.sort(
            key=lambda x: get_install_weight_for_k8s_resource(x[0], x[1]), reverse=True
        )

    # De-duplicate K8sResources
    # Mainly used to remove the extra Namespace and ServiceAccount resources
    deduped_k8s_resources: List[Tuple[K8sResource, int]] = dedup_k8s_resources(
        k8s_resource_list_with_weight
    )
    # deduped_k8s_resources = k8s_resource_list_with_weight
    # logger.debug("K8sResource list")
    # logger.debug(
    #     "\n".join(
    #         "Name: {}, Type: {}, Weight: {}".format(
    #             rsrc.name, rsrc.resource_type, weight
    #         )
    #         for rsrc, weight in deduped_k8s_resources
    #     )
    # )

    # drop the weight from the deduped_k8s_resources tuple
    filtered_k8s_resources: List[K8sResource] = [x[0] for x in deduped_k8s_resources]
    # logger.debug("filtered_k8s_resources: {}".format(filtered_k8s_resources))
    return filtered_k8s_resources

from typing import Optional, List, Dict, Tuple

from typing_extensions import Literal

from phidata.docker.resource.base import DockerResource
from phidata.docker.resource.group import DockerResourceGroup
from phidata.docker.resource.types import DockerResourceInstallOrder
from phidata.utils.log import logger


def get_docker_resources_from_group(
    docker_resource_group: DockerResourceGroup,
    name_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
) -> List[DockerResource]:
    """Parses the DockerResourceGroup and returns an array of DockerResources
    after applying the name & type filters. This function also flattens any
    List[DockerResource] attributes. Eg: it will flatten List[DockerContainer]

    Args:
        docker_resource_group:
        name_filter: filter DockerResources by name
        type_filter: filter DockerResources by type

    Returns:
        List[DockerResource]: List of filtered and flattened DockerResources
    """

    # List of resources to return
    docker_resources: List[DockerResource] = []
    # logger.debug(f"Flattening {docker_resource_group.name}")

    # populate the docker_resources list with the resources
    # Loop over each key of the DockerResourceGroup model
    for resource_key, resource_data in docker_resource_group.__dict__.items():
        # logger.debug("resource: {}".format(resource))
        # logger.debug("resource_data: {}".format(resource_data))

        # Check if the resource is a single DockerResource or a List[DockerResource]
        # If it is a List[DockerResource], flatten the resources, verify each element
        # of the list is a subclass of DockerResource and add to the docker_resources list
        if isinstance(resource_data, list):
            for _r in resource_data:
                if isinstance(_r, DockerResource):
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
                        if type_filter.lower() not in rt.lower():
                            logger.debug(f"  -*- skipping {rt}:{rn}")
                            continue
                    docker_resources.append(_r)  # type: ignore

                    # Add the resource dependencies to the aws_resources list
                    if _r.depends_on is not None:
                        for dep in _r.depends_on:
                            if isinstance(dep, DockerResource):
                                docker_resources.append(dep)

        # If its a single resource, verify that the resource is a subclass of
        # DockerResource and add it to the docker_resources list
        elif isinstance(resource_data, DockerResource):
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
                if type_filter.lower() not in rt.lower():
                    # logger.debug(f"skipping {rt}:{rn}")
                    continue
            docker_resources.append(resource_data)  # type: ignore

    return docker_resources


def get_rank_for_docker_resource(docker_resource_type: DockerResource) -> int:
    """Function which returns the install rank for a DockerResource"""

    resource_type_class_name = docker_resource_type.__class__.__name__
    if resource_type_class_name in DockerResourceInstallOrder.keys():
        install_rank = DockerResourceInstallOrder[resource_type_class_name]
        return install_rank

    return 5000


def dedup_docker_resources(
    docker_resource_list: List[DockerResource],
) -> List[DockerResource]:
    deduped_resources: List[DockerResource] = []
    for rsrc in docker_resource_list:
        if rsrc not in deduped_resources:
            deduped_resources.append(rsrc)
    return deduped_resources


def filter_and_flatten_docker_resource_groups(
    docker_resource_groups: Dict[str, DockerResourceGroup],
    name_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
    app_filter: Optional[str] = None,
    sort_order: Literal["create", "delete"] = "create",
) -> List[DockerResource]:
    """This function parses the docker_resource_groups dict and returns a filtered array of
    DockerResources sorted in the order requested. create == install order, delete == reverse
    Desc:
        1. Iterate through each DockerResourceGroup
        2. If enabled, get the DockerResources from that group which match the filters
        3. Return a list of all DockerResources from 2.

    Args:
        docker_resource_groups: Dict[str, DockerResourceGroup]
            Dict of {resource_group_name : DockerResourceGroup}
        name_filter: Filter DockerResourceGroup by name
        type_filter: Filter DockerResourceGroup by type
        app_filter: Filter DockerResourceGroup by app
        sort_order: create or delete

    Returns:
        List[DockerResource]: List of filtered DockerResources
    """

    logger.debug("Filtering & Flattening DockerResourceGroups")
    # Step 1: Create a list of docker_resources
    docker_resource_list: List[DockerResource] = []
    if docker_resource_groups:
        # Iterate through docker_resource_groups
        for docker_rg_name, docker_rg in docker_resource_groups.items():
            # logger.debug("docker_rg_name: {}".format(docker_rg_name))
            # logger.debug("docker_rg: {}".format(docker_rg))

            # skip disabled DockerResourceGroups
            if not docker_rg.enabled:
                continue

            # skip groups not matching app_filter if provided
            if app_filter is not None and docker_rg_name is not None:
                # logger.debug(f"matching app_filter: {app_filter}")
                # logger.debug(f"with docker_rg_name: {docker_rg_name}")
                if app_filter.lower() not in docker_rg_name.lower():
                    logger.debug(f"  -*- skipping {docker_rg_name}")
                    continue

            _docker_resources = get_docker_resources_from_group(
                docker_rg, name_filter, type_filter
            )
            if _docker_resources:
                docker_resource_list.extend(_docker_resources)

    # Sort the resources in install order
    if sort_order == "create":
        docker_resource_list.sort(key=lambda x: get_rank_for_docker_resource(x))
    elif sort_order == "delete":
        docker_resource_list.sort(
            key=lambda x: get_rank_for_docker_resource(x), reverse=True
        )

    # De-duplicate DockerResources
    deduped_docker_resources: List[DockerResource] = dedup_docker_resources(
        docker_resource_list
    )

    # Implement dependency sorting and drop the weight
    final_docker_resources: List[DockerResource] = []
    for docker_resource in deduped_docker_resources:
        # Logic to follow if resource has dependencies
        if docker_resource.depends_on is not None:
            # If the sort_order is delete
            # 1. Reverse the order of dependencies
            # 2. Remove the dependencies if they are already added to the final_docker_resources
            # 3. Add the resource to be deleted before its dependencies
            # 4. Add the dependencies back in reverse order
            if sort_order == "delete":
                # 1. Reverse the order of dependencies
                docker_resource.depends_on.reverse()
                # 2. Remove the dependencies if they are already added to the final_docker_resources
                for dep in docker_resource.depends_on:
                    if dep in final_docker_resources:
                        logger.debug(
                            f"  -*- Removing {dep.name}, dependency of {docker_resource.name}"
                        )
                        final_docker_resources.remove(dep)
                # 3. Add the resource to be deleted before its dependencies
                if docker_resource not in final_docker_resources:
                    logger.debug(f"  -*- Adding {docker_resource.name}")
                    final_docker_resources.append(docker_resource)

            # Common logic for create and delete
            # When the sort_order is create, the dependencies are added before the resource
            # When the sort_order is delete, the dependencies are added after the resource
            for dep in docker_resource.depends_on:
                if isinstance(dep, DockerResource):
                    if dep not in final_docker_resources:
                        logger.debug(
                            f"  -*- Adding {dep.name}, dependency of {docker_resource.name}"
                        )
                        final_docker_resources.append(dep)

            # If the sort_order is create,
            # add the resource to be created after its dependencies
            if sort_order == "create":
                if docker_resource not in final_docker_resources:
                    logger.debug(f"  -*- Adding {docker_resource.name}")
                    final_docker_resources.append(docker_resource)
        else:
            # Add the resource to be created/deleted
            if docker_resource not in final_docker_resources:
                logger.debug(f"  -*- Adding {docker_resource.name}")
                final_docker_resources.append(docker_resource)

    return final_docker_resources

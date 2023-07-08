from pathlib import Path
from typing import List, Optional

from phi.docker.app.base import DockerApp
from phi.docker.context import DockerBuildContext
from phi.docker.api_client import DockerApiClient
from phi.docker.resource.base import DockerResource
from phi.infra.resource_group import InfraResourceGroup
from phi.workspace.settings import WorkspaceSettings
from phi.utils.log import logger


class DockerResourceGroup(InfraResourceGroup):
    network: str = "bridge"
    # URL for the Docker server. For example, unix:///var/run/docker.sock or tcp://127.0.0.1:1234
    base_url: Optional[str] = None

    apps: Optional[List[DockerApp]] = None
    resources: Optional[List[DockerResource]] = None

    # -*- Cached Data
    _api_client: Optional[DockerApiClient] = None

    @property
    def docker_client(self) -> DockerApiClient:
        if self._api_client is None:
            self._api_client = DockerApiClient(base_url=self.base_url)
        return self._api_client

    def create_resources(
        self,
        group_filter: Optional[str] = None,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        dry_run: Optional[bool] = False,
        auto_confirm: Optional[bool] = False,
        workspace_root: Optional[Path] = None,
        workspace_settings: Optional[WorkspaceSettings] = None,
    ):
        from phi.cli.console import print_info, print_heading, confirm_yes_no
        from phi.docker.resource.types import DockerContainer, DockerResourceInstallOrder

        logger.debug("-*- Creating DockerResources")

        # Build a list of DockerResources to create
        resources_to_create: List[DockerResource] = []
        if self.resources is not None:
            for r in self.resources:
                if r.should_create(
                    group_filter=group_filter,
                    name_filter=name_filter,
                    type_filter=type_filter,
                ):
                    resources_to_create.append(r)

        # Build a list of DockerApps to create
        apps_to_create: List[DockerApp] = []
        if self.apps is not None:
            for app in self.apps:
                if app.should_create(group_filter=group_filter):
                    apps_to_create.append(app)

        # Get the list of DockerResources from the DockerApps
        if len(apps_to_create) > 0:
            logger.debug(f"Found {len(apps_to_create)} apps to create")
            for app in apps_to_create:
                app.add_workspace_settings_to_app(
                    workspace_root=workspace_root, workspace_settings=workspace_settings
                )
                app_resources = app.get_resources(build_context=DockerBuildContext(network=self.network))
                if len(app_resources) > 0:
                    for app_resource in app_resources:
                        if isinstance(app_resource, DockerResource) and app_resource.should_create(
                            name_filter=name_filter, type_filter=type_filter
                        ):
                            resources_to_create.append(app_resource)

        # Sort the DockerResources in install order
        resources_to_create.sort(key=lambda x: DockerResourceInstallOrder.get(x.__class__.__name__, 5000))

        # Deduplicate DockerResources
        deduped_resources_to_create: List[DockerResource] = []
        for r in resources_to_create:
            if r not in deduped_resources_to_create:
                deduped_resources_to_create.append(r)

        # Implement dependency sorting
        final_docker_resources: List[DockerResource] = []
        logger.debug("-*- Building DockerResources dependency graph")
        for docker_resource in deduped_resources_to_create:
            # Logic to follow if resource has dependencies
            if docker_resource.depends_on is not None:
                # Add the dependencies before the resource itself
                for dep in docker_resource.depends_on:
                    if isinstance(dep, DockerResource):
                        if dep not in final_docker_resources:
                            logger.debug(f"-*- Adding {dep.name}, dependency of {docker_resource.name}")
                            final_docker_resources.append(dep)

                # Add the resource to be created after its dependencies
                if docker_resource not in final_docker_resources:
                    logger.debug(f"-*- Adding {docker_resource.name}")
                    final_docker_resources.append(docker_resource)
            else:
                # Add the resource to be created if it has no dependencies
                if docker_resource not in final_docker_resources:
                    logger.debug(f"-*- Adding {docker_resource.name}")
                    final_docker_resources.append(docker_resource)

        # Track the total number of DockerResources to create for validation
        num_resources_to_create: int = len(final_docker_resources)
        num_resources_created: int = 0
        if num_resources_to_create == 0:
            print_info("No DockerResources to create")
            return

        # Validate resources to be created
        if not auto_confirm:
            print_heading("--**-- Confirm resources:")
            for resource in final_docker_resources:
                print_info(f"  -+-> {resource.get_resource_type()}: {resource.get_resource_name()}")
            print_info(f"\nNetwork: {self.network}")
            print_info(f"\nTotal {num_resources_to_create} resources")
            confirm = confirm_yes_no("\nConfirm deploy")
            if not confirm:
                print_info("-*-")
                print_info("-*- Skipping deploy")
                print_info("-*-")
                exit(0)

        for resource in final_docker_resources:
            print_info(f"-==+==- {resource.get_resource_type()}: {resource.get_resource_name()}")
            if isinstance(resource, DockerContainer):
                if resource.network is None and self.network is not None:
                    resource.network = self.network
            # logger.debug(resource)
            try:
                _resource_created = resource.create(docker_client=self.docker_client)
                if _resource_created:
                    num_resources_created += 1
                else:
                    logger.error(
                        f"Resource {resource.get_resource_type()}: {resource.get_resource_name()} could not be created."  # noqa: E501
                    )
                    if workspace_settings is not None and not workspace_settings.continue_on_create_failure:
                        return False
            except Exception as e:
                logger.error(
                    f"-==+==--> Resource {resource.get_resource_type()}: {resource.get_resource_name()} could not be created."  # noqa: E501
                )
                logger.error("Error: {}".format(e))
                logger.error("Skipping resource creation, please fix and try again...")

        print_info(f"\n# Resources created: {num_resources_created}/{num_resources_to_create}")
        if num_resources_to_create == num_resources_created:
            return True

        logger.error(
            f"Resources created: {num_resources_created} do not match resources required: {num_resources_to_create}"  # noqa: E501
        )
        return False

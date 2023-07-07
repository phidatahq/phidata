from typing import Any, Optional, Dict

from phi.resource.base import ResourceBase
from phi.docker.api_client import DockerApiClient
from phi.cli.console import print_info
from phi.utils.log import logger


class DockerResource(ResourceBase):
    """Base class for Docker Resources."""

    # Fields for the resource from the DockerApiClient
    id: Optional[str] = None
    short_id: Optional[str] = None
    attrs: Optional[Dict[str, Any]] = None

    @staticmethod
    def get_from_cluster(docker_client: DockerApiClient) -> Any:
        logger.warning(f"@get_from_cluster method not defined")
        return None

    def _read(self, docker_client: DockerApiClient) -> Any:
        logger.warning(f"@_read method not defined for {self.get_resource_name()}")
        return False

    def read(self, docker_client: DockerApiClient) -> Any:
        """Reads the resource from the docker cluster"""
        if self.use_cache and self.cached_resource is not None:
            return self.cached_resource
        return self._read(docker_client=docker_client)

    def is_active_on_cluster(self, docker_client: DockerApiClient) -> bool:
        """Returns True if the resource is running on the docker cluster"""
        self.cached_resource = self._read(docker_client=docker_client)
        if self.cached_resource is not None:
            return True
        return False

    def _create(self, docker_client: DockerApiClient) -> bool:
        logger.warning(f"@_create method not defined for {self.get_resource_name()}")
        return False

    def create(self, docker_client: DockerApiClient) -> bool:
        """Creates the resource on the docker cluster"""

        # Skip resource creation if skip_create = True
        if self.skip_create:
            print_info(f"Skipping create: {self.get_resource_name()}")
            return True
        if self.use_cache and self.is_active_on_cluster(docker_client=docker_client):
            print_info(
                f"{self.get_resource_type()} {self.get_resource_name()} active on cluster."
            )
            return True
        return self._create(docker_client=docker_client)

    def _update(self, docker_client: DockerApiClient) -> bool:
        logger.warning(f"@_update method not defined for {self.get_resource_name()}")
        return False

    def update(self, docker_client: DockerApiClient) -> bool:
        """Updates the resource on the docker cluster"""

        # Skip resource update if skip_update = True
        if self.skip_update:
            print_info(f"Skipping update: {self.get_resource_name()}")
            return True
        if self.is_active_on_cluster(docker_client=docker_client):
            return self._update(docker_client=docker_client)
        else:
            print_info(
                f"{self.get_resource_type()} {self.get_resource_name()} not active, creating..."
            )
            return self.create(docker_client=docker_client)

    def _delete(self, docker_client: DockerApiClient) -> bool:
        logger.warning(f"@_delete method not defined for {self.get_resource_name()}")
        return False

    def delete(self, docker_client: DockerApiClient) -> bool:
        """Deletes the resource from the docker cluster"""

        # Skip resource deletion if skip_delete = True
        if self.skip_delete:
            print_info(f"Skipping delete: {self.get_resource_name()}")
            return True
        if self.is_active_on_cluster(docker_client=docker_client):
            return self._delete(docker_client=docker_client)
        else:
            print_info(
                f"{self.get_resource_type()} {self.get_resource_name()} not active on cluster."
            )
            return True

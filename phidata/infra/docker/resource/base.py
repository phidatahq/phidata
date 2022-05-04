from typing import Any, Optional, Dict

from phidata.infra.base.resource import InfraResource
from phidata.infra.docker.api_client import DockerApiClient
from phidata.utils.cli_console import print_info
from phidata.utils.log import logger


class DockerResource(InfraResource):
    """Base class for all Docker Resources."""

    # Fields specific to docker resources

    # Fields for the resource from the DockerApiClient
    id: Optional[str] = None
    short_id: Optional[str] = None
    attrs: Optional[Dict[str, Any]] = None

    @staticmethod
    def get_from_cluster(docker_client: DockerApiClient) -> Any:
        logger.error(f"@get_from_cluster method not defined")
        return None

    def _create(self, docker_client: DockerApiClient) -> bool:
        logger.error(f"@_create method not defined for {self.__class__.__name__}")
        return False

    def create(self, docker_client: DockerApiClient) -> bool:
        """Creates the resource on the docker cluster

        Args:
            docker_client: The DockerApiClient for the current cluster
        """
        if self.use_cache and self.is_active_on_cluster(docker_client):
            print_info(
                f"{self.get_resource_type()} {self.get_resource_name()} already active."
            )
            return True
        return self._create(docker_client)

    def _read(self, docker_client: DockerApiClient) -> Any:
        logger.error(f"@_read method not defined for {self.__class__.__name__}")
        return False

    def read(self, docker_client: DockerApiClient) -> Any:
        """Reads the resource from the docker cluster
        Eg:
            * For a Network resource, it will return the DockerNetwork object
            currently running on docker.

        Args:
            docker_client: The DockerApiClient for the current cluster
        """
        if self.use_cache and self.active_resource is not None:
            return self.active_resource
        return self._read(docker_client)

    def _update(self, docker_client: DockerApiClient) -> bool:
        logger.error(f"@_update method not defined for {self.__class__.__name__}")
        return False

    def update(self, docker_client: DockerApiClient) -> bool:
        """Updates the resource on the docker cluster

        Args:
            docker_client: The DockerApiClient for the current cluster
        """
        if self.is_active_on_cluster(docker_client):
            return self._update(docker_client)
        else:
            print_info(
                f"{self.get_resource_type()} {self.get_resource_name()} not active, creating"
            )
            return self.create(docker_client=docker_client)

    def _delete(self, docker_client: DockerApiClient) -> bool:
        logger.error(f"@_delete method not defined for {self.__class__.__name__}")
        return False

    def delete(self, docker_client: DockerApiClient) -> bool:
        """Deletes the resource from the docker cluster

        Args:
            docker_client: The DockerApiClient for the current cluster
        """
        # Skip resource deletion if skip_delete = True
        if self.skip_delete:
            print_info(f"Skipping delete: {self.get_resource_name()}")
            return True
        if self.is_active_on_cluster(docker_client):
            return self._delete(docker_client)
        else:
            print_info(
                f"{self.get_resource_type()} {self.get_resource_name()} not active."
            )
            return True

    def is_active_on_cluster(self, docker_client: DockerApiClient) -> bool:
        """Returns True if the resource is running on the docker cluster"""
        active_resource = self.read(docker_client=docker_client)
        if active_resource is not None:
            return True
        return False

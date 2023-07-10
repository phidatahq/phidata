from typing import Any, Optional, Dict

from phi.infra.resource.base import InfraResource
from phi.docker.api_client import DockerApiClient
from phi.cli.console import print_info
from phi.utils.log import logger


class DockerResource(InfraResource):
    """Base class for Docker Resources."""

    # Fields received from the DockerApiClient
    id: Optional[str] = None
    short_id: Optional[str] = None
    attrs: Optional[Dict[str, Any]] = None

    docker_client: Optional[DockerApiClient] = None

    def get_docker_client(self) -> DockerApiClient:
        if self.docker_client is not None:
            return self.docker_client
        self.docker_client = DockerApiClient()
        return self.docker_client

    @staticmethod
    def get_from_cluster(docker_client: DockerApiClient) -> Any:
        logger.warning("@get_from_cluster method not defined")
        return None

    def _read(self, docker_client: DockerApiClient) -> Any:
        logger.warning(f"@_read method not defined for {self.get_resource_name()}")
        return False

    def read(self, docker_client: DockerApiClient) -> Any:
        """Reads the resource from the docker cluster"""
        if self.use_cache and self.active_resource is not None:
            return self.active_resource

        client: DockerApiClient = docker_client or self.get_docker_client()
        return self._read(client)

    def is_active(self, docker_client: DockerApiClient) -> bool:
        """Returns True if the resource is running on the docker cluster"""
        self.active_resource = self._read(docker_client=docker_client)
        if self.active_resource is not None:
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

        client: DockerApiClient = docker_client or self.get_docker_client()
        if self.use_cache and self.is_active(client):
            self.resource_created = True
            print_info(f"{self.get_resource_type()}: {self.get_resource_name()} already exists")
            return True

        self.resource_created = self._create(client)
        if self.resource_created:
            print_info(f"{self.get_resource_type()}: {self.get_resource_name()} created")
            return True
        logger.error(f"Failed to create {self.get_resource_type()}: {self.get_resource_name()}")
        return False

    def _update(self, docker_client: DockerApiClient) -> bool:
        logger.warning(f"@_update method not defined for {self.get_resource_name()}")
        return False

    def update(self, docker_client: DockerApiClient) -> bool:
        """Updates the resource on the docker cluster"""

        # Skip resource update if skip_update = True
        if self.skip_update:
            print_info(f"Skipping update: {self.get_resource_name()}")
            return True

        client: DockerApiClient = docker_client or self.get_docker_client()
        if self.is_active(client):
            self.resource_updated = self._update(client)
            if self.resource_updated:
                print_info(f"{self.get_resource_type()}: {self.get_resource_name()} updated")
                return True
        else:
            print_info(f"{self.get_resource_type()}: {self.get_resource_name()} not active, creating...")
            return self.create(client)
        logger.error(f"Failed to update {self.get_resource_type()}: {self.get_resource_name()}")
        return False

    def _delete(self, docker_client: DockerApiClient) -> bool:
        logger.warning(f"@_delete method not defined for {self.get_resource_name()}")
        return False

    def delete(self, docker_client: DockerApiClient) -> bool:
        """Deletes the resource from the docker cluster"""

        # Skip resource deletion if skip_delete = True
        if self.skip_delete:
            print_info(f"Skipping delete: {self.get_resource_name()}")
            return True
        if self.is_active(docker_client=docker_client):
            self.resource_deleted = self._delete(docker_client=docker_client)
            if self.resource_deleted:
                print_info(f"{self.get_resource_type()}: {self.get_resource_name()} deleted")
                return True
        else:
            print_info(f"{self.get_resource_type()}: {self.get_resource_name()} not active on cluster")
            return True
        logger.error(f"Failed to delete {self.get_resource_type()}: {self.get_resource_name()}")
        return False

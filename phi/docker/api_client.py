from typing import Optional, Any

from phi.utils.log import logger


class DockerApiClient:
    def __init__(self, base_url: Optional[str] = None):
        super().__init__()
        self.base_url: Optional[str] = base_url

        # Type: docker.DockerClient
        self._api_client: Optional[Any] = None
        logger.debug("**-+-** DockerApiClient created")

    def create_api_client(self) -> Optional[Any]:
        """Create a docker.DockerClient"""
        import docker

        logger.debug("Creating docker.DockerClient")
        api_client = None
        try:
            if self.base_url is None:
                api_client = docker.from_env(timeout=30)
            else:
                api_client = docker.DockerClient(base_url=self.base_url)
        except Exception as e:
            logger.error("Could not connect to docker. Please confirm docker is installed and running")
            logger.error(e)
            exit(0)
        return api_client

    @property
    def api_client(self) -> Optional[Any]:
        if self._api_client is None:
            self._api_client = self.create_api_client()
        return self._api_client

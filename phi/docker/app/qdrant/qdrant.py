from typing import Optional, Dict

from phi.docker.app.base import DockerApp, WorkspaceVolumeType, AppVolumeType, ContainerContext  # noqa: F401
from phi.utils.log import logger


class Qdrant(DockerApp):
    name: str = "qdrant"
    image_name: str = "qdrant/qdrant"
    image_tag: str = "v1.3.1"
    open_container_port: bool = True
    container_port: int = 6333
    host_port: int = 6333

    # -*- Qdrant Volume
    # Create a volume for qdrant storage
    create_qdrant_volume: bool = True
    # If qdrant_storage_dir is provided, mount this directory relative to workspace_root
    # from host machine to container
    qdrant_storage_dir: Optional[str] = None
    # Otherwise, mount a volume named qdrant_volume_name to the container
    # If qdrant_volume_name is not provided, use default volume name
    qdrant_volume_name: Optional[str] = None
    # Path to mount the qdrant volume inside the container
    qdrant_storage_container_path: str = "/qdrant/storage"

    def build_container_volumes_docker(self, container_context: ContainerContext) -> Dict[str, dict]:
        from phi.utils.defaults import get_default_volume_name

        if self.workspace_root is None:
            logger.error("Invalid workspace_root")
            return {}

        # container_volumes is a dictionary which configures the volumes to mount
        # inside the container. The key is either the host path or a volume name,
        # and the value is a dictionary with 2 keys:
        #   bind - The path to mount the volume inside the container
        #   mode - Either rw to mount the volume read/write, or ro to mount it read-only.
        # For example:
        # {
        #   '/home/user1/': {'bind': '/mnt/vol2', 'mode': 'rw'},
        #   '/var/www': {'bind': '/mnt/vol1', 'mode': 'ro'}
        # }
        container_volumes = self.container_volumes or {}

        # Create a volume for Qdrant Storage
        if self.create_qdrant_volume:
            qdrant_volume_host = self.qdrant_volume_name or get_default_volume_name(self.get_app_name())

            if self.qdrant_storage_dir is not None:
                qdrant_volume_host = str(self.workspace_root.joinpath(self.qdrant_storage_dir))

            logger.debug(f"Mounting: {qdrant_volume_host}")
            logger.debug(f"\tto: {self.qdrant_storage_container_path}")
            container_volumes[qdrant_volume_host] = {
                "bind": self.qdrant_storage_container_path,
                "mode": "rw",
            }

        return container_volumes

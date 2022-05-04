from typing import Optional, Any, Dict, Union, List

from docker.models.volumes import Volume
from docker.errors import NotFound

from phidata.infra.docker.api_client import DockerApiClient
from phidata.infra.docker.resource.base import DockerResource
from phidata.utils.log import logger


class DockerVolume(DockerResource):
    resource_type: str = "Volume"

    # driver (str) – Name of the driver used to create the volume
    driver: Optional[str] = None
    # driver_opts (dict) – Driver options as a key-value dictionary
    driver_opts: Optional[Dict[str, Any]] = None
    # labels (dict) – Labels to set on the volume
    labels: Optional[Dict[str, Any]] = None

    def _create(self, docker_client: DockerApiClient) -> bool:
        """Creates the Volume on docker

        Args:
            docker_client: The DockerApiClient for the current cluster
        """

        logger.debug("Creating: {}".format(self.get_resource_name()))
        volume_name: Optional[str] = self.name
        volume_object: Optional[Volume] = None

        try:
            volume_object = docker_client.api_client.volumes.create(
                name=volume_name,
                driver=self.driver,
                driver_opts=self.driver_opts,
                labels=self.labels,
            )
            if volume_object is not None:
                self.verbose_log("Volume Created: {}".format(volume_object.name))
            else:
                self.verbose_log("Volume could not be created")
            # self.verbose_log("Volume {}".format(volume_object.attrs))
        except Exception as e:
            raise

        # By this step the volume should be created
        # Get the data from the volume object
        self.verbose_log("Validating volume is created")
        if volume_object is not None:
            _id: str = volume_object.id
            _short_id: str = volume_object.short_id
            _name: str = volume_object.name
            _attrs: str = volume_object.attrs
            if _id:
                self.verbose_log("_id: {}".format(_id))
                self.id = _id
            if _short_id:
                self.verbose_log("_short_id: {}".format(_short_id))
                self.short_id = _short_id
            if _name:
                self.verbose_log("_name: {}".format(_name))
            if _attrs:
                self.verbose_log("_attrs: {}".format(_attrs))
                # TODO: use json_to_dict(_attrs)
                self.attrs = _attrs  # type: ignore

            # TODO: Validate that the volume object is created properly
            self.active_resource = volume_object
            self.active_resource_class = Volume
            return True
        return False

    def _read(self, docker_client: DockerApiClient) -> Any:
        """Returns a Volume object if the volume is active on the docker_client"""

        logger.debug("Reading: {}".format(self.get_resource_name()))
        volume_name: Optional[str] = self.name

        try:
            volume_list: Optional[
                List[Volume]
            ] = docker_client.api_client.volumes.list()
            # self.verbose_log("volume_list: {}".format(volume_list))
            if volume_list is not None:
                for volume in volume_list:
                    if volume.name == volume_name:
                        self.verbose_log(f"Volume {volume_name} exists")
                        self.active_resource = volume
                        self.active_resource_class = Volume
                        return volume
        except Exception:
            self.verbose_log(f"Volume {volume_name} not found")

        return None

    def _delete(self, docker_client: DockerApiClient) -> bool:
        """Deletes the Volume on docker

        Args:
            docker_client: The DockerApiClient for the current cluster
        """

        logger.debug("Deleting: {}".format(self.get_resource_name()))
        volume_name: Optional[str] = self.name
        volume_object: Optional[Volume] = self._read(docker_client)
        # Return True if there is no Volume to delete
        if volume_object is None:
            return True

        # Delete Volume
        try:
            self.active_resource = None
            volume_object.remove(force=True)
        except Exception as e:
            logger.exception("Error while deleting volume: {}".format(e))

        # Validate that the volume is deleted
        self.verbose_log("Validating volume is deleted")
        try:
            self.verbose_log("Reloading volume_object: {}".format(volume_object))
            volume_object.reload()
        except NotFound as e:
            self.verbose_log("Got NotFound Exception, Volume is deleted")
            return True

        return False

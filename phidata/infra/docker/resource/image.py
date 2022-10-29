from typing import Optional, Any, Dict, List

from phidata.infra.docker.api_client import DockerApiClient
from phidata.infra.docker.resource.base import DockerResource
from phidata.utils.cli_console import print_info, print_error
from phidata.utils.log import logger


class DockerImage(DockerResource):
    resource_type: str = "Image"

    # Docker image name, usually as repo/image
    name: str
    # Docker image tag
    tag: Optional[str] = None

    # Path to the directory containing the Dockerfile
    path: Optional[str] = None
    # Path to the Dockerfile within the build context
    dockerfile: Optional[str] = None

    # Print the build log
    print_build_log: bool = False
    # Push the image to the registry. Similar to the docker push command.
    push_image: bool = False
    print_push_output: bool = False

    # Remove intermediate containers.
    # The docker build command defaults to --rm=true,
    # The docker api kept the old default of False to preserve backward compatibility
    rm: Optional[bool] = True
    # Always remove intermediate containers, even after unsuccessful builds
    forcerm: Optional[bool] = None
    # HTTP timeout
    timeout: Optional[int] = None
    # Downloads any updates to the FROM image in Dockerfiles
    pull: Optional[bool] = None
    # Skips docker cache when set to True
    # i.e. rebuilds all layes of the image
    skip_docker_cache: Optional[bool] = None
    # A dictionary of build arguments
    buildargs: Optional[Dict[str, Any]] = None
    # A dictionary of limits applied to each container created by the build process. Valid keys:
    # memory (int): set memory limit for build
    # memswap (int): Total memory (memory + swap), -1 to disable swap
    # cpushares (int): CPU shares (relative weight)
    # cpusetcpus (str): CPUs in which to allow execution, e.g. "0-3", "0,1"
    container_limits: Optional[Dict[str, Any]] = None
    # Size of /dev/shm in bytes. The size must be greater than 0. If omitted the system uses 64MB
    shmsize: Optional[int] = None
    # A dictionary of labels to set on the image
    labels: Optional[Dict[str, Any]] = None
    # A list of images used for build cache resolution
    cache_from: Optional[List[Any]] = None
    # Name of the build-stage to build in a multi-stage Dockerfile
    target: Optional[str] = None
    # networking mode for the run commands during build
    network_mode: Optional[str] = None
    # Squash the resulting images layers into a single layer.
    squash: Optional[bool] = None
    # Extra hosts to add to /etc/hosts in building containers, as a mapping of hostname to IP address.
    extra_hosts: Optional[Dict[str, Any]] = None
    # Platform in the format os[/arch[/variant]].
    platform: Optional[str] = None
    # Isolation technology used during build. Default: None.
    isolation: Optional[str] = None
    # If True, and if the docker client configuration file (~/.docker/config.json by default)
    # contains a proxy configuration, the corresponding environment variables
    # will be set in the container being built.
    use_config_proxy: Optional[bool] = None

    # so that images arent deleted when phi ws down is run
    skip_delete: bool = True
    image_build_id: Optional[str] = None

    def get_resource_name(self) -> Optional[str]:
        return self.get_name_tag()

    def get_name_tag(self) -> str:
        image_name_tag = self.name
        if self.tag:
            image_name_tag = f"{image_name_tag}:{self.tag}"
        return image_name_tag

    def build_image(self, docker_client: DockerApiClient) -> Optional[Any]:
        from docker import DockerClient
        from docker.errors import BuildError, APIError

        print_info(f"Building image: {self.get_name_tag()}")
        nocache = self.skip_docker_cache
        pull = self.pull
        if self.path is not None:
            print_info(f"\t  path: {self.path}")
        if self.dockerfile is not None:
            print_info(f"    dockerfile: {self.dockerfile}")
        logger.debug(f"platform: {self.platform}")
        logger.debug(f"nocache: {nocache}")
        logger.debug(f"pull: {pull}")
        try:
            _api_client: DockerClient = docker_client.api_client
            build_stream = _api_client.api.build(
                tag=self.get_name_tag(),
                path=self.path,
                dockerfile=self.dockerfile,
                nocache=nocache,
                rm=self.rm,
                forcerm=self.forcerm,
                timeout=self.timeout,
                pull=pull,
                buildargs=self.buildargs,
                container_limits=self.container_limits,
                shmsize=self.shmsize,
                labels=self.labels,
                cache_from=self.cache_from,
                target=self.target,
                network_mode=self.network_mode,
                squash=self.squash,
                extra_hosts=self.extra_hosts,
                platform=self.platform,
                isolation=self.isolation,
                use_config_proxy=self.use_config_proxy,
                decode=True,
            )
            for build_log in build_stream:
                line = build_log.get("stream", None)
                if line is None:
                    continue
                if len(line) < 5:
                    continue
                line = line.strip()
                if "Step" in line and self.print_build_log:
                    print_info(line)
                else:
                    logger.debug(line)
                if "ERROR" in line or "error" in line:
                    print_error(f"Image build failed: {self.get_name_tag()}")
                    print_error(line)
                    return None
                if build_log.get("aux", None) is not None:
                    logger.debug("build_log['aux'] :{}".format(build_log["aux"]))
                    self.image_build_id = build_log.get("aux", {}).get("ID")
            if self.push_image:
                print_info(f"Pushing {self.get_name_tag()}")
                push_progress = None
                prev_push_progress = None
                for push_output in _api_client.images.push(
                    repository=self.name,
                    tag=self.tag,
                    stream=True,
                    decode=True,
                ):
                    if push_output.get("error", None) is not None:
                        print_error(push_output["error"])
                        print_error(f"Push failed for {self.get_name_tag()}")
                        print_error(
                            "If you are using a private registry, make sure you are logged in"
                        )
                    if self.print_push_output and push_output.get("status", None) in (
                        "Pushing",
                        "Pushed",
                    ):
                        push_progress = push_output.get("progress", None)
                        if push_progress != prev_push_progress:
                            print_info(push_progress)
                            prev_push_progress = push_progress
                    if push_output.get("aux", {}).get("Size", 0) > 0:
                        print_info(f"Push complete: {push_output.get('aux', {})}")
            return self._read(docker_client)
        except TypeError as type_error:
            print_error(type_error)
            # print_error("TypeError: {}".format(type_error))
        except BuildError as build_error:
            print_error(build_error)
            # print_error("BuildError: {}".format(build_error))
        except APIError as api_err:
            print_error(api_err)
            # print_error("ApiError: {}".format(api_err))
        return None

    def _create(self, docker_client: DockerApiClient) -> bool:
        """Creates the image

        Args:
            docker_client: The DockerApiClient for the current cluster
        """
        from docker.models.images import Image

        logger.debug("Creating: {}".format(self.get_resource_name()))

        try:
            image_object = self.build_image(docker_client)
            if image_object is not None and isinstance(image_object, Image):
                logger.debug("Image built: {}".format(image_object))
                self.active_resource = image_object
                self.active_resource_class = Image
                return True
            else:
                logger.error("Image {} could not be built".format(self.tag))
        except Exception as e:
            logger.exception(e)
            logger.error("Error while creating image: {}".format(e))
            raise

        return False

    def _read(self, docker_client: DockerApiClient) -> Any:
        """Returns an Image object if available"""
        from docker import DockerClient
        from docker.models.images import Image
        from docker.errors import ImageNotFound, NotFound

        logger.debug("Reading: {}".format(self.get_name_tag()))
        try:
            _api_client: DockerClient = docker_client.api_client
            image_object: Optional[List[Image]] = _api_client.images.get(
                name=self.get_name_tag()
            )
            if image_object is not None and isinstance(image_object, Image):
                logger.debug("Image found: {}".format(image_object))
                self.active_resource = image_object
                return image_object
        except (NotFound, ImageNotFound) as not_found_err:
            logger.debug(f"Image {self.tag} not found")

        return None

    def _update(self, docker_client: DockerApiClient) -> bool:
        """Updates the Image

        Args:
            docker_client: The DockerApiClient for the current cluster
        """
        logger.debug("Updating: {}".format(self.get_resource_name()))
        return self._create(docker_client=docker_client)

    def _delete(self, docker_client: DockerApiClient) -> bool:
        """Deletes the Image

        Args:
            docker_client: The DockerApiClient for the current cluster
        """
        from docker import DockerClient
        from docker.models.images import Image

        logger.debug("Deleting: {}".format(self.get_resource_name()))
        image_object: Optional[Image] = self._read(docker_client)
        # Return True if there is no image to delete
        if image_object is None:
            logger.debug("No image to delete")
            return True

        # Delete Image
        try:
            self.active_resource = None
            logger.debug("Deleting image: {}".format(self.tag))
            _api_client: DockerClient = docker_client.api_client
            _api_client.images.remove(image=self.tag, force=True)
            return True
        except Exception as e:
            logger.exception("Error while deleting image: {}".format(e))

        return False

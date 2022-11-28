from typing import Optional, Any, Dict, List

from phidata.infra.aws.resource.base import AwsResource
from phidata.utils.log import logger


class EcsContainer(AwsResource):
    """
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html
    """

    resource_type = "EcsContainer"
    service_name = "ecs"

    # The name of a container.
    # If you're linking multiple containers together in a task definition, the name of one container can be entered in
    # the links of another container to connect the containers.
    name: str
    # The image used to start a container.
    image: str
    # The private repository authentication credentials to use.
    repository_credentials: Optional[Dict[str, Any]] = None
    # The number of cpu units reserved for the container.
    cpu: Optional[int] = None
    # The amount (in MiB) of memory to present to the container.
    memory: Optional[int] = None
    # The soft limit (in MiB) of memory to reserve for the container.
    memory_reservation: Optional[int] = None
    # The links parameter allows containers to communicate with each other without the need for port mappings.
    links: Optional[List[str]] = None
    # The list of port mappings for the container. Port mappings allow containers to access ports on the host container
    # instance to send or receive traffic.
    port_mappings: Optional[List[Dict[str, Any]]] = None
    # If the essential parameter of a container is marked as true , and that container fails or stops for any reason,
    # all other containers that are part of the task are stopped. If the essential parameter of a container is marked
    # as false , its failure doesn't affect the rest of the containers in a task. If this parameter is omitted,
    # a container is assumed to be essential.
    essential: Optional[bool] = None
    # The entry point that's passed to the container.
    entry_point: Optional[List[str]] = None
    # The command that's passed to the container.
    command: Optional[List[str]] = None
    # The environment variables to pass to a container.
    environment: Optional[List[Dict[str, Any]]] = None
    # The entry point that's passed to the container.
    environment_files: Optional[List[Dict[str, Any]]] = None
    # The mount points for data volumes in your container.
    mount_points: Optional[List[Dict[str, Any]]] = None
    # Data volumes to mount from another container.
    volumes_from: Optional[List[Dict[str, Any]]] = None
    # Linux-specific modifications that are applied to the container, such as Linux kernel capabilities.
    linux_parameters: Optional[Dict[str, Any]] = None
    # The secrets to pass to the container.
    secrets: Optional[List[Dict[str, Any]]] = None
    # The dependencies defined for container startup and shutdown.
    depends_on: Optional[List[Dict[str, Any]]] = None
    # Time duration (in seconds) to wait before giving up on resolving dependencies for a container.
    start_timeout: Optional[int] = None
    # Time duration (in seconds) to wait before the container is forcefully killed if it doesn't exit normally.
    stop_timeout: Optional[int] = None
    # The hostname to use for your container.
    hostname: Optional[str] = None
    # The user to use inside the container.
    user: Optional[str] = None
    # The working directory to run commands inside the container in.
    working_directory: Optional[str] = None
    # When this parameter is true, networking is disabled within the container.
    disable_networking: Optional[bool] = None
    # When this parameter is true, the container is given elevated privileges
    # on the host container instance (similar to the root user).
    privileged: Optional[bool] = None
    readonly_root_filesystem: Optional[bool] = None
    dns_servers: Optional[List[str]] = None
    dns_search_domains: Optional[List[str]] = None
    extra_hosts: Optional[List[Dict[str, Any]]] = None
    docker_security_options: Optional[List[str]] = None
    interactive: Optional[bool] = None
    pseudo_terminal: Optional[bool] = None
    docker_labels: Optional[Dict[str, Any]] = None
    ulimits: Optional[List[Dict[str, Any]]] = None
    log_configuration: Optional[Dict[str, Any]] = None
    health_check: Optional[Dict[str, Any]] = None
    system_controls: Optional[List[Dict[str, Any]]] = None
    resource_requirements: Optional[List[Dict[str, Any]]] = None
    firelens_configuration: Optional[Dict[str, Any]] = None

    def get_container_definition(self) -> Dict[str, Any]:

        container_definition: Dict[str, Any] = {}
        if self.name is not None:
            container_definition["name"] = self.name
        if self.image is not None:
            container_definition["image"] = self.image
        if self.repository_credentials is not None:
            container_definition["repositoryCredentials"] = self.repository_credentials
        if self.cpu is not None:
            container_definition["cpu"] = self.cpu
        if self.memory is not None:
            container_definition["memory"] = self.memory
        if self.memory_reservation is not None:
            container_definition["memoryReservation"] = self.memory_reservation
        if self.links is not None:
            container_definition["links"] = self.links
        if self.port_mappings is not None:
            container_definition["portMappings"] = self.port_mappings
        if self.essential is not None:
            container_definition["essential"] = self.essential
        if self.entry_point is not None:
            container_definition["entryPoint"] = self.entry_point
        if self.command is not None:
            container_definition["command"] = self.command
        if self.environment is not None:
            container_definition["environment"] = self.environment
        if self.environment_files is not None:
            container_definition["environmentFiles"] = self.environment_files
        if self.mount_points is not None:
            container_definition["mountPoints"] = self.mount_points
        if self.volumes_from is not None:
            container_definition["volumesFrom"] = self.volumes_from
        if self.linux_parameters is not None:
            container_definition["linuxParameters"] = self.linux_parameters
        if self.secrets is not None:
            container_definition["secrets"] = self.secrets
        if self.depends_on is not None:
            container_definition["dependsOn"] = self.depends_on
        if self.start_timeout is not None:
            container_definition["startTimeout"] = self.start_timeout
        if self.stop_timeout is not None:
            container_definition["stopTimeout"] = self.stop_timeout
        if self.hostname is not None:
            container_definition["hostname"] = self.hostname
        if self.user is not None:
            container_definition["user"] = self.user
        if self.working_directory is not None:
            container_definition["workingDirectory"] = self.working_directory
        if self.disable_networking is not None:
            container_definition["disableNetworking"] = self.disable_networking
        if self.privileged is not None:
            container_definition["privileged"] = self.privileged
        if self.readonly_root_filesystem is not None:
            container_definition[
                "readonlyRootFilesystem"
            ] = self.readonly_root_filesystem
        if self.dns_servers is not None:
            container_definition["dnsServers"] = self.dns_servers
        if self.dns_search_domains is not None:
            container_definition["dnsSearchDomains"] = self.dns_search_domains
        if self.extra_hosts is not None:
            container_definition["extraHosts"] = self.extra_hosts
        if self.docker_security_options is not None:
            container_definition["dockerSecurityOptions"] = self.docker_security_options
        if self.interactive is not None:
            container_definition["interactive"] = self.interactive
        if self.pseudo_terminal is not None:
            container_definition["pseudoTerminal"] = self.pseudo_terminal
        if self.docker_labels is not None:
            container_definition["dockerLabels"] = self.docker_labels
        if self.ulimits is not None:
            container_definition["ulimits"] = self.ulimits
        if self.log_configuration is not None:
            container_definition["logConfiguration"] = self.log_configuration
        if self.health_check is not None:
            container_definition["healthCheck"] = self.health_check
        if self.system_controls is not None:
            container_definition["systemControls"] = self.system_controls
        if self.resource_requirements is not None:
            container_definition["resourceRequirements"] = self.resource_requirements
        if self.firelens_configuration is not None:
            container_definition["firelensConfiguration"] = self.firelens_configuration

        return container_definition

    def container_definition_up_to_date(
        self, container_definition: Dict[str, Any]
    ) -> bool:
        """This is not working"""

        from phidata.utils.compare import compare_dicts

        if self.name is not None:
            if container_definition.get("name") != self.name:
                logger.debug(
                    "{} != {}".format(self.name, container_definition.get("name"))
                )
                return False
        if self.image is not None:
            if container_definition.get("image") != self.image:
                logger.debug(
                    "{} != {}".format(self.image, container_definition.get("image"))
                )
                return False
        if self.repository_credentials is not None:
            if not compare_dicts(
                self.repository_credentials,
                container_definition.get("repositoryCredentials"),
            ):
                logger.debug(
                    "{} != {}".format(
                        self.repository_credentials,
                        container_definition.get("repositoryCredentials"),
                    )
                )
                return False
        if self.cpu is not None:
            if container_definition.get("cpu") != self.cpu:
                logger.debug(
                    "{} != {}".format(self.cpu, container_definition.get("cpu"))
                )
                return False
        if self.memory is not None:
            if container_definition.get("memory") != self.memory:
                logger.debug(
                    "{} != {}".format(self.memory, container_definition.get("memory"))
                )
                return False
        if self.memory_reservation is not None:
            if container_definition.get("memoryReservation") != self.memory_reservation:
                logger.debug(
                    "{} != {}".format(
                        self.memory_reservation,
                        container_definition.get("memoryReservation"),
                    )
                )
                return False
        if self.links is not None:
            if container_definition.get("links") != self.links:
                logger.debug(
                    "{} != {}".format(self.links, container_definition.get("links"))
                )
                return False
        if self.port_mappings is not None:
            port_mappings_from_api = container_definition.get("portMappings")
            if port_mappings_from_api is not None and len(
                port_mappings_from_api
            ) == len(self.port_mappings):
                for i, port_mapping in enumerate(self.port_mappings):
                    if not compare_dicts(
                        port_mapping,
                        port_mappings_from_api[i],
                    ):
                        logger.debug(
                            "{} != {}".format(
                                port_mapping,
                                port_mappings_from_api[i],
                            )
                        )
                        return False
            else:
                logger.debug("portMappings not up to date")
                return False
        if self.essential is not None:
            if container_definition.get("essential") != self.essential:
                logger.debug(
                    "{} != {}".format(
                        self.essential, container_definition.get("essential")
                    )
                )
                return False
        if self.entry_point is not None:
            if container_definition.get("entryPoint") != self.entry_point:
                logger.debug(
                    "{} != {}".format(
                        self.entry_point, container_definition.get("entryPoint")
                    )
                )
                return False
        if self.command is not None:
            if container_definition.get("command") != self.command:
                logger.debug(
                    "{} != {}".format(self.command, container_definition.get("command"))
                )
                return False
        if self.environment is not None:
            if container_definition.get("environment") != self.environment:
                logger.debug(
                    "{} != {}".format(
                        self.environment, container_definition.get("environment")
                    )
                )
                return False
        if self.environment_files is not None:
            if container_definition.get("environmentFiles") != self.environment_files:
                logger.debug(
                    "{} != {}".format(
                        self.environment_files,
                        container_definition.get("environmentFiles"),
                    )
                )
                return False
        if self.mount_points is not None:
            if container_definition.get("mountPoints") != self.mount_points:
                logger.debug(
                    "{} != {}".format(
                        self.mount_points, container_definition.get("mountPoints")
                    )
                )
                return False
        if self.volumes_from is not None:
            if container_definition.get("volumesFrom") != self.volumes_from:
                logger.debug(
                    "{} != {}".format(
                        self.volumes_from, container_definition.get("volumesFrom")
                    )
                )
                return False
        if self.linux_parameters is not None:
            if container_definition.get("linuxParameters") != self.linux_parameters:
                logger.debug(
                    "{} != {}".format(
                        self.linux_parameters,
                        container_definition.get("linuxParameters"),
                    )
                )
                return False
        if self.secrets is not None:
            if container_definition.get("secrets") != self.secrets:
                logger.debug(
                    "{} != {}".format(self.secrets, container_definition.get("secrets"))
                )
                return False
        if self.depends_on is not None:
            if container_definition.get("dependsOn") != self.depends_on:
                logger.debug(
                    "{} != {}".format(
                        self.depends_on, container_definition.get("dependsOn")
                    )
                )
                return False
        if self.start_timeout is not None:
            if container_definition.get("startTimeout") != self.start_timeout:
                logger.debug(
                    "{} != {}".format(
                        self.start_timeout, container_definition.get("startTimeout")
                    )
                )
                return False
        if self.stop_timeout is not None:
            if container_definition.get("stopTimeout") != self.stop_timeout:
                logger.debug(
                    "{} != {}".format(
                        self.stop_timeout, container_definition.get("stopTimeout")
                    )
                )
                return False
        if self.hostname is not None:
            if container_definition.get("hostname") != self.hostname:
                logger.debug(
                    "{} != {}".format(
                        self.hostname, container_definition.get("hostname")
                    )
                )
                return False
        if self.user is not None:
            if container_definition.get("user") != self.user:
                logger.debug(
                    "{} != {}".format(self.user, container_definition.get("user"))
                )
                return False
        if self.working_directory is not None:
            if container_definition.get("workingDirectory") != self.working_directory:
                logger.debug(
                    "{} != {}".format(
                        self.working_directory,
                        container_definition.get("workingDirectory"),
                    )
                )
                return False
        if self.disable_networking is not None:
            if container_definition.get("disableNetworking") != self.disable_networking:
                logger.debug(
                    "{} != {}".format(
                        self.disable_networking,
                        container_definition.get("disableNetworking"),
                    )
                )
                return False
        if self.privileged is not None:
            if container_definition.get("privileged") != self.privileged:
                logger.debug(
                    "{} != {}".format(
                        self.privileged, container_definition.get("privileged")
                    )
                )
                return False
        if self.readonly_root_filesystem is not None:
            if (
                container_definition.get("readonlyRootFilesystem")
                != self.readonly_root_filesystem
            ):
                logger.debug(
                    "{} != {}".format(
                        self.readonly_root_filesystem,
                        container_definition.get("readonlyRootFilesystem"),
                    )
                )
                return False
        if self.dns_servers is not None:
            if container_definition.get("dnsServers") != self.dns_servers:
                logger.debug(
                    "{} != {}".format(
                        self.dns_servers, container_definition.get("dnsServers")
                    )
                )
                return False
        if self.dns_search_domains is not None:
            if container_definition.get("dnsSearchDomains") != self.dns_search_domains:
                logger.debug(
                    "{} != {}".format(
                        self.dns_search_domains,
                        container_definition.get("dnsSearchDomains"),
                    )
                )
                return False
        if self.extra_hosts is not None:
            if container_definition.get("extraHosts") != self.extra_hosts:
                logger.debug(
                    "{} != {}".format(
                        self.extra_hosts, container_definition.get("extraHosts")
                    )
                )
                return False
        if self.docker_security_options is not None:
            if (
                container_definition.get("dockerSecurityOptions")
                != self.docker_security_options
            ):
                logger.debug(
                    "{} != {}".format(
                        self.docker_security_options,
                        container_definition.get("dockerSecurityOptions"),
                    )
                )
                return False
        if self.interactive is not None:
            if container_definition.get("interactive") != self.interactive:
                logger.debug(
                    "{} != {}".format(
                        self.interactive, container_definition.get("interactive")
                    )
                )
                return False
        if self.pseudo_terminal is not None:
            if container_definition.get("pseudoTerminal") != self.pseudo_terminal:
                logger.debug(
                    "{} != {}".format(
                        self.pseudo_terminal, container_definition.get("pseudoTerminal")
                    )
                )
                return False
        if self.docker_labels is not None:
            if container_definition.get("dockerLabels") != self.docker_labels:
                logger.debug(
                    "{} != {}".format(
                        self.docker_labels, container_definition.get("dockerLabels")
                    )
                )
                return False
        if self.ulimits is not None:
            if container_definition.get("ulimits") != self.ulimits:
                logger.debug(
                    "{} != {}".format(self.ulimits, container_definition.get("ulimits"))
                )
                return False
        if self.log_configuration is not None:
            if container_definition.get("logConfiguration") != self.log_configuration:
                logger.debug(
                    "{} != {}".format(
                        self.log_configuration,
                        container_definition.get("logConfiguration"),
                    )
                )
                return False
        if self.health_check is not None:
            if container_definition.get("healthCheck") != self.health_check:
                logger.debug(
                    "{} != {}".format(
                        self.health_check, container_definition.get("healthCheck")
                    )
                )
                return False
        if self.system_controls is not None:
            if container_definition.get("systemControls") != self.system_controls:
                logger.debug(
                    "{} != {}".format(
                        self.system_controls, container_definition.get("systemControls")
                    )
                )
                return False
        if self.resource_requirements is not None:
            if (
                container_definition.get("resourceRequirements")
                != self.resource_requirements
            ):
                logger.debug(
                    "{} != {}".format(
                        self.resource_requirements,
                        container_definition.get("resourceRequirements"),
                    )
                )
                return False
        if self.firelens_configuration is not None:
            if (
                container_definition.get("firelensConfiguration")
                != self.firelens_configuration
            ):
                logger.debug(
                    "{} != {}".format(
                        self.firelens_configuration,
                        container_definition.get("firelensConfiguration"),
                    )
                )
                return False

        return True

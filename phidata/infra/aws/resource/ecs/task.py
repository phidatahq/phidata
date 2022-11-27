from typing import Optional, Any, Dict, List, Literal

from phidata.infra.aws.api_client import AwsApiClient
from phidata.infra.aws.resource.base import AwsResource
from phidata.infra.aws.resource.ecs.container import EcsContainer
from phidata.infra.aws.resource.ecs.volume import EcsVolume
from phidata.utils.cli_console import print_info, print_error
from phidata.utils.log import logger


class EcsTask(AwsResource):
    """
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html
    """

    resource_type = "EcsTask"
    service_name = "ecs"

    # Name of the task definition.
    # Used as task definition family.
    name: str
    # The family for a task definition.
    # Use name as family if not provided
    # You can use it track multiple versions of the same task definition.
    # The family is used as a name for your task definition.
    family: Optional[str] = None
    # The short name or full Amazon Resource Name (ARN) of the IAM role that containers in this task can assume.
    task_role_arn: Optional[str] = None
    execution_role_arn: Optional[str] = None
    # Networking mode to use for the containers in the task.
    # The valid values are none, bridge, awsvpc, and host.
    # If no network mode is specified, the default is bridge.
    network_mode: Optional[Literal["bridge", "host", "awsvpc", "none"]] = None
    # A list of container definitions that describe the different containers that make up the task.
    containers: Optional[List[EcsContainer]] = None
    volumes: Optional[List[EcsVolume]] = None
    placement_constraints: Optional[List[Dict[str, Any]]] = None
    requires_compatibilities: Optional[List[str]] = None
    cpu: Optional[str] = None
    memory: Optional[str] = None
    tags: Optional[List[Dict[str, str]]] = None
    pid_mode: Optional[Literal["host", "task"]] = None
    ipc_mode: Optional[Literal["host", "task", "none"]] = None
    proxy_configuration: Optional[Dict[str, Any]] = None
    inference_accelerators: Optional[List[Dict[str, Any]]] = None
    ephemeral_storage: Optional[Dict[str, Any]] = None
    runtime_platform: Optional[Dict[str, Any]] = None

    def get_task_family(self):
        return self.family or self.name

    def _create(self, aws_client: AwsApiClient) -> bool:
        """Create EcsTask"""
        print_info(f"Creating {self.get_resource_type()}: {self.get_resource_name()}")

        # create a dict of args which are not null, otherwise aws type validation fails
        not_null_args: Dict[str, Any] = {}
        if self.task_role_arn is not None:
            not_null_args["taskRoleArn"] = self.task_role_arn
        if self.execution_role_arn is not None:
            not_null_args["executionRoleArn"] = self.execution_role_arn
        if self.network_mode is not None:
            not_null_args["networkMode"] = self.network_mode
        if self.containers is not None:
            container_definitions = [
                c.get_container_definition() for c in self.containers
            ]
            not_null_args["containerDefinitions"] = container_definitions
        if self.volumes is not None:
            volume_definitions = [v.get_volume_definition() for v in self.volumes]
            not_null_args["volumes"] = volume_definitions
        if self.placement_constraints is not None:
            not_null_args["placementConstraints"] = self.placement_constraints
        if self.requires_compatibilities is not None:
            not_null_args["requiresCompatibilities"] = self.requires_compatibilities
        if self.cpu is not None:
            not_null_args["cpu"] = self.cpu
        if self.memory is not None:
            not_null_args["memory"] = self.memory
        if self.tags is not None:
            not_null_args["tags"] = self.tags
        if self.pid_mode is not None:
            not_null_args["pidMode"] = self.pid_mode
        if self.ipc_mode is not None:
            not_null_args["ipcMode"] = self.ipc_mode
        if self.proxy_configuration is not None:
            not_null_args["proxyConfiguration"] = self.proxy_configuration
        if self.inference_accelerators is not None:
            not_null_args["inferenceAccelerators"] = self.inference_accelerators
        if self.ephemeral_storage is not None:
            not_null_args["ephemeralStorage"] = self.ephemeral_storage
        if self.runtime_platform is not None:
            not_null_args["runtimePlatform"] = self.runtime_platform

        # Register EcsTask
        service_client = self.get_service_client(aws_client)
        try:
            create_response = service_client.register_task_definition(
                family=self.get_task_family(),
                **not_null_args,
            )
            logger.debug(f"EcsTask: {create_response}")
            resource_dict = create_response.get("taskDefinition", {})

            # Validate resource creation
            if resource_dict is not None:
                print_info(f"EcsTask created: {self.get_resource_name()}")
                self.active_resource = create_response
                return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be created.")
            print_error(e)
        return False

    def _read(self, aws_client: AwsApiClient) -> Optional[Any]:
        """Read EcsTask"""
        from botocore.exceptions import ClientError

        logger.debug(f"Reading {self.get_resource_type()}: {self.get_resource_name()}")
        service_client = self.get_service_client(aws_client)
        try:
            describe_response = service_client.describe_task_definition(
                taskDefinition=self.get_task_family()
            )
            logger.debug(f"EcsTask: {describe_response}")
            resource = describe_response.get("taskDefinition", None)
            if resource is not None:
                # compare the task definition with the current state
                # if there is a difference, create a new task definition
                # TODO: fix the task_definition_up_to_date function
                # if self.task_definition_up_to_date(task_definition=resource):
                self.active_resource = resource
        except ClientError as ce:
            logger.debug(f"ClientError: {ce}")
        except Exception as e:
            print_error(f"Error reading {self.get_resource_type()}.")
            print_error(e)
        return self.active_resource

    def _delete(self, aws_client: AwsApiClient) -> bool:
        """Delete EcsTask"""
        print_info(f"Deleting {self.get_resource_type()}: {self.get_resource_name()}")

        service_client = self.get_service_client(aws_client)
        self.active_resource = None
        try:
            # Get the task definition revisions
            list_response = service_client.list_task_definitions(
                familyPrefix=self.get_task_family(), sort="DESC"
            )
            logger.debug(f"EcsTask: {list_response}")
            task_definition_arns = list_response.get("taskDefinitionArns", [])
            if task_definition_arns:
                # Delete all revisions
                for task_definition_arn in task_definition_arns:
                    service_client.deregister_task_definition(
                        taskDefinition=task_definition_arn
                    )
                print_info(f"EcsTask deleted: {self.get_resource_name()}")
                return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be deleted.")
            print_error("Please try again or delete resources manually.")
            print_error(e)
        return False

    def _update(self, aws_client: AwsApiClient) -> bool:
        """Update EcsTask"""
        print_info(f"Updating {self.get_resource_type()}: {self.get_resource_name()}")

        return self._create(aws_client)

    def task_definition_up_to_date(self, task_definition: Dict[str, Any]) -> bool:
        """Return True if task_definition from the cluster matches the current state"""

        # Validate container definitions
        if self.containers is not None:
            container_definitions_from_api = task_definition.get("containerDefinitions")
            # Compare the container definitions from the api with the current containers
            # The order of the container definitions should also match
            if container_definitions_from_api is not None and len(
                container_definitions_from_api
            ) == len(self.containers):
                for i, container in enumerate(self.containers):
                    if not container.container_definition_up_to_date(
                        container_definition=container_definitions_from_api[i]
                    ):
                        logger.debug("Container definitions not up to date")
                        return False
            else:
                logger.debug("Container definitions not up to date")
                return False

        # Validate volumes
        if self.volumes is not None:
            volume_definitions_from_api = task_definition.get("volumes")
            # Compare the volume definitions from the api with the current volumes
            # The order of the volume definitions should also match
            if volume_definitions_from_api is not None and len(
                volume_definitions_from_api
            ) == len(self.volumes):
                for i, volume in enumerate(self.volumes):
                    if not volume.volume_definition_up_to_date(
                        volume_definition=volume_definitions_from_api[i]
                    ):
                        logger.debug("Volume definitions not up to date")
                        return False
            else:
                logger.debug("Volume definitions not up to date")
                return False

        # Validate other properties
        if self.task_role_arn is not None:
            if self.task_role_arn != task_definition.get("taskRoleArn"):
                logger.debug(
                    "{} != {}".format(
                        self.task_role_arn, task_definition.get("taskRoleArn")
                    )
                )
                return False
        if self.execution_role_arn is not None:
            if self.execution_role_arn != task_definition.get("executionRoleArn"):
                logger.debug(
                    "{} != {}".format(
                        self.execution_role_arn, task_definition.get("executionRoleArn")
                    )
                )
                return False
        if self.network_mode is not None:
            if self.network_mode != task_definition.get("networkMode"):
                logger.debug(
                    "{} != {}".format(
                        self.network_mode, task_definition.get("networkMode")
                    )
                )
                return False
        if self.placement_constraints is not None:
            if self.placement_constraints != task_definition.get(
                "placementConstraints"
            ):
                logger.debug(
                    "{} != {}".format(
                        self.placement_constraints,
                        task_definition.get("placementConstraints"),
                    )
                )
                return False
        if self.requires_compatibilities is not None:
            if self.requires_compatibilities != task_definition.get(
                "requiresCompatibilities"
            ):
                logger.debug(
                    "{} != {}".format(
                        self.requires_compatibilities,
                        task_definition.get("requiresCompatibilities"),
                    )
                )
                return False
        if self.cpu is not None:
            if self.cpu != task_definition.get("cpu"):
                logger.debug("{} != {}".format(self.cpu, task_definition.get("cpu")))
                return False
        if self.memory is not None:
            if self.memory != task_definition.get("memory"):
                logger.debug(
                    "{} != {}".format(self.memory, task_definition.get("memory"))
                )
                return False
        if self.tags is not None:
            if self.tags != task_definition.get("tags"):
                logger.debug("{} != {}".format(self.tags, task_definition.get("tags")))
                return False
        if self.pid_mode is not None:
            if self.pid_mode != task_definition.get("pidMode"):
                logger.debug(
                    "{} != {}".format(self.pid_mode, task_definition.get("pidMode"))
                )
                return False
        if self.ipc_mode is not None:
            if self.ipc_mode != task_definition.get("ipcMode"):
                logger.debug(
                    "{} != {}".format(self.ipc_mode, task_definition.get("ipcMode"))
                )
                return False
        if self.proxy_configuration is not None:
            if self.proxy_configuration != task_definition.get("proxyConfiguration"):
                logger.debug(
                    "{} != {}".format(
                        self.proxy_configuration,
                        task_definition.get("proxyConfiguration"),
                    )
                )
                return False
        if self.inference_accelerators is not None:
            if self.inference_accelerators != task_definition.get(
                "inferenceAccelerators"
            ):
                logger.debug(
                    "{} != {}".format(
                        self.inference_accelerators,
                        task_definition.get("inferenceAccelerators"),
                    )
                )
                return False
        if self.ephemeral_storage is not None:
            if self.ephemeral_storage != task_definition.get("ephemeralStorage"):
                logger.debug(
                    "{} != {}".format(
                        self.ephemeral_storage, task_definition.get("ephemeralStorage")
                    )
                )
                return False
        if self.runtime_platform is not None:
            if self.runtime_platform != task_definition.get("runtimePlatform"):
                logger.debug(
                    "{} != {}".format(
                        self.runtime_platform, task_definition.get("runtimePlatform")
                    )
                )
                return False

        return True

from typing import Optional, Any, Dict, List
from textwrap import dedent

from phidata.aws.api_client import AwsApiClient
from phidata.aws.resource.base import AwsResource
from phidata.aws.resource.iam.role import IamRole
from phidata.utils.cli_console import print_info, print_error, print_warning
from phidata.utils.log import logger
import json


class LambdaFunction(AwsResource):
    """
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html
    """

    resource_type = "lambda"
    service_name = "lambda"

    # Name of the LambdaFunction.
    function_name: str
    runtime: Optional[str] = None
    role: Optional[str] = None
    handler: Optional[str] = None
    code: Optional[Dict] = None
    description: Optional[str] = None
    timeout: Optional[int] = None
    memory_size: Optional[int] = None
    publish: Optional[bool] = None
    vpc_config: Optional[Dict] = None
    package_type: Optional[str] = None
    dead_letter_config: Optional[Dict] = None
    environment: Optional[Dict] = None
    kms_key_arn: Optional[str] = None
    tracing_config: Optional[Dict] = None
    tags: Optional[Dict] = None
    layers: Optional[List[str]] = None
    file_system_configs: Optional[List[Dict]] = None
    image_config: Optional[Dict] = None
    code_signing_config_arn: Optional[str] = None
    architectures: Optional[List[str]] = None
    ephemeral_storage: Optional[Dict] = None
    snap_start: Optional[Dict] = None

    def _create(self, aws_client: AwsApiClient) -> bool:
        """Creates the LambdaFunction

        Args:
            aws_client: The AwsApiClient for the current LambdaFunction
        """
        print_info(f"Creating {self.get_resource_type()}: {self.get_resource_name()}")

        # role = self.role
        # if role is None:
        #     # Create the IamRole and get role
        #     execution_role = self.get_execution_role()
        #     try:
        #         execution_role.create(aws_client)
        #         role = execution_role.read(aws_client).arn
        #         print_info(f"ARN for {execution_role.name}: {role}")
        #     except Exception as e:
        #         print_error("IamRole creation failed, please fix and try again")
        #         print_error(e)
        #         return False

        self.role = "arn:aws:iam::386435111151:role/service-role/AmazonSageMakerServiceCatalogProductsLambdaRole"

        # create a dict of args which are not null, otherwise aws type validation fails
        not_null_args: Dict[str, Any] = {}
        if self.function_name is not None:
            not_null_args["FunctionName"] = self.function_name
        if self.runtime is not None:
            not_null_args["Runtime"] = self.runtime
        if self.role is not None:
            not_null_args["Role"] = self.role
        if self.handler is not None:
            not_null_args["Handler"] = self.handler
        if self.code is not None:
            not_null_args["Code"] = self.code
        if self.description is not None:
            not_null_args["Description"] = self.description
        if self.timeout is not None:
            not_null_args["Timeout"] = self.timeout
        if self.memory_size is not None:
            not_null_args["MemorySize"] = self.memory_size
        if self.publish is not None:
            not_null_args["Publish"] = self.publish
        if self.vpc_config is not None:
            not_null_args["VpcConfig"] = self.vpc_config
        if self.package_type is not None:
            not_null_args["PackageType"] = self.package_type
        if self.dead_letter_config is not None:
            not_null_args["DeadLetterConfig"] = self.dead_letter_config
        if self.environment is not None:
            not_null_args["Environment"] = self.environment
        if self.kms_key_arn is not None:
            not_null_args["KmsKeyArn"] = self.kms_key_arn
        if self.tracing_config is not None:
            not_null_args["TracingConfig"] = self.tracing_config
        if self.tags is not None:
            not_null_args["tags"] = self.tags
        if self.layers is not None:
            not_null_args["Layers"] = self.layers
        if self.file_system_configs is not None:
            not_null_args["FileSystemConfigs"] = self.file_system_configs
        if self.image_config is not None:
            not_null_args["ImageConfig"] = self.image_config
        if self.code_signing_config_arn is not None:
            not_null_args["CodeSigningConfigArn"] = self.code_signing_config_arn
        if self.architectures is not None:
            not_null_args["Architectures"] = self.architectures
        if self.ephemeral_storage is not None:
            not_null_args["EphemeralStorage"] = self.ephemeral_storage
        if self.snap_start is not None:
            not_null_args["SnapStart"] = self.snap_start

        # Create LambdaFunction
        try:
            service_client = self.get_service_client(aws_client)
            logger.debug(f"Create Args: {not_null_args}")
            logger.debug(self.function_name)
            create_response = service_client.create_function(
                **not_null_args,
            )
            logger.debug(f"Create Response: {create_response}")
            resource_dict = create_response.get("LambdaFunctions", {})

            # Validate resource creation
            if resource_dict is not None:
                print_info(f"LambdaFunction created: {self.get_resource_name()}")
                self.active_resource = create_response
                return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be created.")
            print_error(e)
        return False

    # def post_create(self, aws_client: AwsApiClient) -> bool:
    #     # Wait for LambdaFunction to be created
    #     if self.wait_for_creation:
    #         try:
    #             print_info(f"Waiting for {self.get_resource_type()} to be created.")
    #             waiter = self.get_service_client(aws_client).get_waiter(
    #                 "load_balancer_exists"
    #             )
    #             waiter.wait(
    #                 Names=[self.get_resource_name()],
    #                 WaiterConfig={
    #                     "Delay": self.waiter_delay,
    #                     "MaxAttempts": self.waiter_max_attempts,
    #                 },
    #             )
    #         except Exception as e:
    #             print_error("Waiter failed.")
    #             print_error(e)
    #     # Read the LambdaFunction
    #     elb = self._read(aws_client)
    #     if elb is None:
    #         print_error(
    #             f"Error reading {self.get_resource_type()}. Please get DNS name manually."
    #         )
    #     else:
    #         dns_name = elb.get("DNSName", None)
    #         print_info(f"LambdaFunction DNS: http://{dns_name}")
    #     return True

    def _read(self, aws_client: AwsApiClient) -> Optional[Any]:
        """Returns the LambdaFunction

        Args:
            aws_client: The AwsApiClient for the current LambdaFunction
        """
        logger.debug(f"Reading {self.get_resource_type()}: {self.get_resource_name()}")

        from botocore.exceptions import ClientError

        service_client = self.get_service_client(aws_client)
        try:
            describe_response = service_client.get_function(
                FunctionName=self.function_name
            )
            logger.debug(f"Describe Response: {describe_response}")
            # Need to test this piece.
            resource_list = describe_response.get("LambdaFunctions", None)

            if resource_list is not None and isinstance(resource_list, list):
                self.active_resource = resource_list[0]
        except ClientError as ce:
            logger.debug(f"ClientError: {ce}")
        except Exception as e:
            print_error(f"Error reading {self.get_resource_type()}.")
            print_error(e)
        return self.active_resource

    def _delete(self, aws_client: AwsApiClient) -> bool:
        """Deletes the LambdaFunction

        Args:
            aws_client: The AwsApiClient for the current LambdaFunction
        """
        print_info(f"Deleting {self.get_resource_type()}: {self.get_resource_name()}")

        service_client = self.get_service_client(aws_client)
        self.active_resource = None

        try:
            lambda_name = self.function_name
            if lambda_name is None:
                print_warning(f"{self.get_resource_type()} not found.")
                return True
            delete_response = service_client.delete_function(FunctionName=lambda_name)
            logger.debug(f"Delete Response: {delete_response}")
            print_info(
                f"{self.get_resource_type()}: {self.get_resource_name()} deleted"
            )
            return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be deleted.")
            print_error("Please try again or delete resources manually.")
            print_error(e)
        return False

    # def post_delete(self, aws_client: AwsApiClient) -> bool:
    #     # Wait for LambdaFunction to be deleted
    #     if self.wait_for_deletion:
    #         try:
    #             print_info(f"Waiting for {self.get_resource_type()} to be deleted.")
    #             waiter = self.get_service_client(aws_client).get_waiter(
    #                 "load_balancers_deleted"
    #             )
    #             waiter.wait(
    #                 Names=[self.get_resource_name()],
    #                 WaiterConfig={
    #                     "Delay": self.waiter_delay,
    #                     "MaxAttempts": self.waiter_max_attempts,
    #                 },
    #             )
    #         except Exception as e:
    #             print_error("Waiter failed.")
    #             print_error(e)
    #     return True

    def get_arn(self, aws_client: AwsApiClient) -> Optional[str]:
        lambda_fn = self._read(aws_client)
        if lambda_fn is None:
            return None
        lambda_arn = lambda_fn.get("LambdaFunctionArn", None)
        return lambda_arn

    # def get_execution_role(self) -> IamRole:
    #     policy_arns = [
    #         "arn:aws:iam::aws:policy/LambdaBasicExecution",
    #     ]
    #     # if self.add_execution_role_policy_arns is not None and isinstance(
    #     #     self.add_execution_role_policy_arns, list
    #     # ):
    #     #     policy_arns.extend(self.add_execution_role_policy_arns)

    #     return IamRole(
    #         name=f"{self.function_name}-execution-role",
    #         assume_role_policy_document=dedent(
    #             """\
    #         {
    #           "Version": "2012-10-17",
    #           "Statement": [
    #             {
    #               "Sid":""
    #               "Effect": "Allow",
    #               "Principal": {
    #                 "Service": "lambda.amazonaws.com"
    #               },
    #               "Action": "sts:AssumeRole"
    #             }
    #           ]
    #         }
    #         """
    #         ),
    #         policy_arns=policy_arns,
    #     )

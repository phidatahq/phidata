from typing import Optional, Any, Dict, List

from phidata.aws.api_client import AwsApiClient
from phidata.aws.resource.base import AwsResource
from phidata.utils.cli_console import print_info, print_error, print_warning
from phidata.utils.log import logger


class Invoke(AwsResource):
    """
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html
    """

    resource_type = "invoke"
    service_name = "invoke"

    # Name of the Invoke.
    function_name: str
    invocation_type: Optional[str] = None
    log_type: Optional[str] = None
    client_context: Optional[str] = None
    payload: Optional[str] = None
    qualifier: Optional[str] = None

    def _create(self, aws_client: AwsApiClient) -> bool:
        """Creates the Invoke

        Args:
            aws_client: The AwsApiClient for the current Invoke
        """
        print_info(f"Creating {self.get_resource_type()}: {self.get_resource_name()}")

        # create a dict of args which are not null, otherwise aws type validation fails
        not_null_args: Dict[str, Any] = {}
        if self.function_name is not None:
            not_null_args["FunctionName"] = self.function_name
        if self.invocation_type is not None:
            not_null_args["InvocationType"] = self.invocation_type
        if self.log_type is not None:
            not_null_args["LogType"] = self.log_type
        if self.client_context is not None:
            not_null_args["ClientContext"] = self.client_context
        if self.payload is not None:
            not_null_args["Payload"] = self.payload
        if self.qualifier is not None:
            not_null_args["Qualifier"] = self.qualifier

        # Create Invoke
        service_client = self.get_service_client(aws_client)
        try:
            create_response = service_client.invoke(
                Name=self.name,
                **not_null_args,
            )
            logger.debug(f"Create Response: {create_response}")
            resource_dict = create_response.get("Invokes", {})

            # Validate resource creation
            if resource_dict is not None:
                print_info(f"Invoke created: {self.get_resource_name()}")
                self.active_resource = create_response
                return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be created.")
            print_error(e)
        return False

    # def post_create(self, aws_client: AwsApiClient) -> bool:
    #     # Wait for Invoke to be created
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
    #     # Read the Invoke
    #     elb = self._read(aws_client)
    #     if elb is None:
    #         print_error(
    #             f"Error reading {self.get_resource_type()}. Please get DNS name manually."
    #         )
    #     else:
    #         dns_name = elb.get("DNSName", None)
    #         print_info(f"Invoke DNS: http://{dns_name}")
    #     return True

    # def _read(self, aws_client: AwsApiClient) -> Optional[Any]:
    #     """Returns the Invoke

    #     Args:
    #         aws_client: The AwsApiClient for the current Invoke
    #     """
    #     logger.debug(f"Reading {self.get_resource_type()}: {self.get_resource_name()}")

    #     from botocore.exceptions import ClientError

    #     service_client = self.get_service_client(aws_client)
    #     try:
    #         describe_response = service_client.describe_load_balancers(
    #             Names=[self.name]
    #         )
    #         logger.debug(f"Describe Response: {describe_response}")
    #         resource_list = describe_response.get("Invokes", None)

    #         if resource_list is not None and isinstance(resource_list, list):
    #             self.active_resource = resource_list[0]
    #     except ClientError as ce:
    #         logger.debug(f"ClientError: {ce}")
    #     except Exception as e:
    #         print_error(f"Error reading {self.get_resource_type()}.")
    #         print_error(e)
    #     return self.active_resource

    # def _delete(self, aws_client: AwsApiClient) -> bool:
    #     """Deletes the Invoke

    #     Args:
    #         aws_client: The AwsApiClient for the current Invoke
    #     """
    #     print_info(f"Deleting {self.get_resource_type()}: {self.get_resource_name()}")

    #     service_client = self.get_service_client(aws_client)
    #     self.active_resource = None

    #     try:
    #         lambda_name = self.function_name
    #         if lambda_name is None:
    #             print_warning(f"{self.get_resource_type()} not found.")
    #             return True
    #         delete_response = service_client.delete_function(
    #             FunctionName=lambda_name
    #         )
    #         logger.debug(f"Delete Response: {delete_response}")
    #         print_info(
    #             f"{self.get_resource_type()}: {self.get_resource_name()} deleted"
    #         )
    #         return True
    #     except Exception as e:
    #         print_error(f"{self.get_resource_type()} could not be deleted.")
    #         print_error("Please try again or delete resources manually.")
    #         print_error(e)
    #     return False

    # # def post_delete(self, aws_client: AwsApiClient) -> bool:
    # #     # Wait for Invoke to be deleted
    # #     if self.wait_for_deletion:
    # #         try:
    # #             print_info(f"Waiting for {self.get_resource_type()} to be deleted.")
    # #             waiter = self.get_service_client(aws_client).get_waiter(
    # #                 "load_balancers_deleted"
    # #             )
    # #             waiter.wait(
    # #                 Names=[self.get_resource_name()],
    # #                 WaiterConfig={
    # #                     "Delay": self.waiter_delay,
    # #                     "MaxAttempts": self.waiter_max_attempts,
    # #                 },
    # #             )
    # #         except Exception as e:
    # #             print_error("Waiter failed.")
    # #             print_error(e)
    # #     return True

    # def get_arn(self, aws_client: AwsApiClient) -> Optional[str]:
    #     lb = self._read(aws_client)
    #     if lb is None:
    #         return None
    #     lb_arn = lb.get("InvokeArn", None)
    #     return lb_arn

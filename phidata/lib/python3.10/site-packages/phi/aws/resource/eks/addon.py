from typing import Optional, Any, Dict
from typing_extensions import Literal

from phi.aws.api_client import AwsApiClient
from phi.aws.resource.base import AwsResource
from phi.cli.console import print_info
from phi.utils.log import logger


class EksAddon(AwsResource):
    """
    Reference:
    - https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/eks.html
    """

    resource_type: Optional[str] = "EksAddon"
    service_name: str = "eks"

    # Addon name
    name: str
    # EKS cluster name
    cluster_name: str
    # Addon version
    version: Optional[str] = None

    service_account_role_arn: Optional[str] = None
    resolve_conflicts: Optional[Literal["OVERWRITE", "NONE", "PRESERVE"]] = None
    client_request_token: Optional[str] = None
    tags: Optional[Dict[str, str]] = None

    preserve: Optional[bool] = False

    # provided by api on create
    created_at: Optional[str] = None
    status: Optional[str] = None

    wait_for_create: bool = False
    wait_for_delete: bool = False
    wait_for_update: bool = False

    def _create(self, aws_client: AwsApiClient) -> bool:
        """Creates the EksAddon

        Args:
            aws_client: The AwsApiClient for the current cluster
        """
        print_info(f"Creating {self.get_resource_type()}: {self.get_resource_name()}")

        # create a dict of args which are not null, otherwise aws type validation fails
        not_null_args: Dict[str, Any] = {}
        if self.version:
            not_null_args["addonVersion"] = self.version
        if self.service_account_role_arn:
            not_null_args["serviceAccountRoleArn"] = self.service_account_role_arn
        if self.resolve_conflicts:
            not_null_args["resolveConflicts"] = self.resolve_conflicts
        if self.client_request_token:
            not_null_args["clientRequestToken"] = self.client_request_token
        if self.tags:
            not_null_args["tags"] = self.tags

        # Step 1: Create EksAddon
        service_client = self.get_service_client(aws_client)
        try:
            create_response = service_client.create_addon(
                clusterName=self.cluster_name,
                addonName=self.name,
                **not_null_args,
            )
            logger.debug(f"EksAddon: {create_response}")
            # logger.debug(f"EksAddon type: {type(create_response)}")

            # Validate Cluster creation
            self.created_at = create_response.get("addon", {}).get("createdAt", None)
            self.status = create_response.get("addon", {}).get("status", None)
            logger.debug(f"created_at: {self.created_at}")
            logger.debug(f"status: {self.status}")
            if self.created_at is not None:
                print_info(f"EksAddon created: {self.name}")
                self.active_resource = create_response
                return True
        except service_client.exceptions.ResourceInUseException:
            print_info(f"Addon already exists: {self.name}")
            return True
        except Exception as e:
            logger.error(f"{self.get_resource_type()} could not be created.")
            logger.error(e)
        return False

    def post_create(self, aws_client: AwsApiClient) -> bool:
        # Wait for Addon to be created
        if self.wait_for_create:
            try:
                print_info(f"Waiting for {self.get_resource_type()} to be active.")
                waiter = self.get_service_client(aws_client).get_waiter("addon_active")
                waiter.wait(
                    clusterName=self.cluster_name,
                    addonName=self.name,
                    WaiterConfig={
                        "Delay": self.waiter_delay,
                        "MaxAttempts": self.waiter_max_attempts,
                    },
                )
            except Exception:
                # logger.error(f"Waiter failed: {awe}")
                pass
        return True

    def _read(self, aws_client: AwsApiClient) -> Optional[Any]:
        """Returns the EksAddon

        Args:
            aws_client: The AwsApiClient for the current cluster
        """
        from botocore.exceptions import ClientError

        logger.debug(f"Reading {self.get_resource_type()}: {self.get_resource_name()}")

        service_client = self.get_service_client(aws_client)
        try:
            describe_response = service_client.describe_addon(clusterName=self.cluster_name, addonName=self.name)
            # logger.debug(f"EksAddon: {describe_response}")
            # logger.debug(f"EksAddon type: {type(describe_response)}")
            addon_dict = describe_response.get("addon", {})

            self.created_at = addon_dict.get("createdAt", None)
            self.status = addon_dict.get("status", None)
            logger.debug(f"EksAddon created_at: {self.created_at}")
            logger.debug(f"EksAddon status: {self.status}")
            if self.created_at is not None:
                logger.debug(f"EksAddon found: {self.name}")
                self.active_resource = describe_response
        except ClientError as ce:
            logger.debug(f"ClientError: {ce}")
        except Exception as e:
            logger.error(f"Error reading {self.get_resource_type()}.")
            logger.error(e)
        return self.active_resource

    def _delete(self, aws_client: AwsApiClient) -> bool:
        """Deletes the EksAddon

        Args:
            aws_client: The AwsApiClient for the current cluster
        """
        print_info(f"Deleting {self.get_resource_type()}: {self.get_resource_name()}")

        # create a dict of args which are not null, otherwise aws type validation fails
        not_null_args: Dict[str, Any] = {}
        if self.preserve:
            not_null_args["preserve"] = self.preserve

        # Step 1: Delete EksAddon
        service_client = self.get_service_client(aws_client)
        self.active_resource = None
        try:
            delete_response = service_client.delete_addon(
                clusterName=self.cluster_name, addonName=self.name, **not_null_args
            )
            logger.debug(f"EksAddon: {delete_response}")
            # logger.debug(f"EksAddon type: {type(delete_response)}")
            return True
        except Exception as e:
            logger.error(f"{self.get_resource_type()} could not be deleted.")
            logger.error("Please try again or delete resources manually.")
            logger.error(e)
        return False

    def post_delete(self, aws_client: AwsApiClient) -> bool:
        # Wait for Addon to be deleted
        if self.wait_for_delete:
            try:
                print_info(f"Waiting for {self.get_resource_type()} to be deleted.")
                waiter = self.get_service_client(aws_client).get_waiter("addon_deleted")
                waiter.wait(
                    clusterName=self.cluster_name,
                    addonName=self.name,
                    WaiterConfig={
                        "Delay": self.waiter_delay,
                        "MaxAttempts": self.waiter_max_attempts,
                    },
                )
            except Exception as awe:
                logger.error(f"Waiter failed: {awe}")
        return True

from pathlib import Path
from typing import Optional, Any, Dict, List
from typing_extensions import Literal

from pydantic import BaseModel

from phidata.infra.aws.api_client import AwsApiClient
from phidata.infra.aws.resource.base import AwsResource
from phidata.utils.cli_console import print_info, print_error, print_warning
from phidata.utils.log import logger


class SecretSummary(BaseModel):
    SecretArn: Optional[str] = None
    Name: Optional[str] = None


class Secret(AwsResource):
    """
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/secretsmanager.html
    """

    resource_type = "Secret"
    service_name = "secretsmanager"

    # The name of the new secret.
    name: str
    client_request_token: Optional[str] = None
    # The description of the secret.
    description: Optional[str] = None
    kms_key_id: Optional[str] = None
    # The binary data to encrypt and store in the new version of the secret.
    # We recommend that you store your binary data in a file and then pass the contents of the file as a parameter.
    secret_binary: Optional[bytes] = None
    # The text data to encrypt and store in this new version of the secret.
    # We recommend you use a JSON structure of key/value pairs for your secret value.
    # Either SecretString or SecretBinary must have a value, but not both.
    secret_string: Optional[str] = None
    # A list of tags to attach to the secret.
    tags: Optional[List[Dict[str, str]]] = None
    # A list of Regions and KMS keys to replicate secrets.
    add_replica_regions: Optional[List[Dict[str, str]]] = None
    # Specifies whether to overwrite a secret with the same name in the destination Region.
    force_overwrite_replica_secret: Optional[str] = None

    secret_arn: Optional[str] = None
    secret_resource_name: Optional[str] = None

    # If True, stores the secret arn in the file `secret_summary_file`
    store_secret_summary: bool = False
    # Path for the secret_summary_file
    secret_summary_file: Optional[Path] = None

    def _create(self, aws_client: AwsApiClient) -> bool:
        """Creates the Secret

        Args:
            aws_client: The AwsApiClient for the current volume
        """
        print_info(f"Creating {self.get_resource_type()}: {self.get_resource_name()}")

        # Step 1: Build Secret configuration
        # create a dict of args which are not null, otherwise aws type validation fails
        not_null_args: Dict[str, Any] = {}
        if self.client_request_token:
            not_null_args["ClientRequestToken"] = self.client_request_token
        if self.description:
            not_null_args["Description"] = self.description
        if self.kms_key_id:
            not_null_args["KmsKeyId"] = self.kms_key_id
        if self.secret_binary:
            not_null_args["SecretBinary"] = self.secret_binary
        if self.secret_string:
            not_null_args["SecretString"] = self.secret_string
        if self.tags:
            not_null_args["Tags"] = self.tags
        if self.add_replica_regions:
            not_null_args["AddReplicaRegions"] = self.add_replica_regions
        if self.force_overwrite_replica_secret:
            not_null_args[
                "ForceOverwriteReplicaSecret"
            ] = self.force_overwrite_replica_secret

        # Step 2: Create Secret
        service_client = self.get_service_client(aws_client)
        try:
            created_resource = service_client.create_secret(
                Name=self.name,
                **not_null_args,
            )
            logger.debug(f"Secret: {created_resource}")

            # Validate Secret creation
            self.secret_arn = created_resource.get("ARN", None)
            self.secret_resource_name = created_resource.get("Name", None)
            logger.debug(f"secret_arn: {self.secret_arn}")
            logger.debug(f"secret_resource_name: {self.secret_resource_name}")
            if self.secret_arn is not None:
                print_info(f"Secret created: {self.name}")
                self.active_resource = created_resource
                return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be created.")
            print_error(e)
        return False

    def post_create(self, aws_client: AwsApiClient) -> bool:

        # Store secret summary if needed
        if self.store_secret_summary:
            if self.secret_summary_file is None:
                print_error("secret_summary_file not provided")
                return False

            try:
                secret_arn = self.secret_arn
                secret_resource_name = self.secret_resource_name

                secret_summary = SecretSummary(
                    SecretArn=secret_arn, Name=secret_resource_name
                )
                if not self.secret_summary_file.exists():
                    self.secret_summary_file.parent.mkdir(parents=True, exist_ok=True)
                    self.secret_summary_file.touch(exist_ok=True)
                self.secret_summary_file.write_text(secret_summary.json(indent=2))
                print_info(f"SecretSummary stored at: {str(self.secret_summary_file)}")
            except Exception as e:
                print_error("Could not writing SecretSummary to file")
                print_error(e)

        return True

    def _read(self, aws_client: AwsApiClient) -> Optional[Any]:
        """Returns the Secret

        Args:
            aws_client: The AwsApiClient for the current volume
        """
        logger.debug(f"Reading {self.get_resource_type()}: {self.get_resource_name()}")

        from botocore.exceptions import ClientError

        service_client = self.get_service_client(aws_client)
        try:
            volume = None
            for _volume in service_client.volumes.all():
                _volume_tags = _volume.tags
                # logger.debug(f"Found volume: {_volume}")
                # logger.debug(f"Tags: {_volume_tags}")
                if _volume_tags is not None and isinstance(_volume_tags, list):
                    for _tag in _volume_tags:
                        if _tag["Key"] == self.name_tag and _tag["Value"] == self.name:
                            volume = _volume
                            break
                # found volume, break loop
                if volume is not None:
                    break

            if volume is None:
                logger.debug("No Secret found")
                return None

            volume.load()
            create_time = volume.create_time
            self.volume_id = volume.volume_id
            logger.debug(f"create_time: {create_time}")
            logger.debug(f"volume_id: {self.volume_id}")
            if create_time is not None:
                logger.debug(f"Secret found: {self.name}")
                self.active_resource = volume
        except ClientError as ce:
            logger.debug(f"ClientError: {ce}")
        except Exception as e:
            print_error(f"Error reading {self.get_resource_type()}.")
            print_error(e)
        return self.active_resource

    def _delete(self, aws_client: AwsApiClient) -> bool:
        """Deletes the Secret

        Args:
            aws_client: The AwsApiClient for the current volume
        """
        print_info(f"Deleting {self.get_resource_type()}: {self.get_resource_name()}")

        self.active_resource = None
        try:
            volume = self._read(aws_client)
            logger.debug(f"Secret: {volume}")
            if volume is None:
                logger.warning(f"No {self.get_resource_type()} to delete")
                return True

            # detach the volume from all instances
            for attachment in volume.attachments:
                device = attachment.get("Device", None)
                instance_id = attachment.get("InstanceId", None)
                print_info(
                    f"Detaching volume from device: {device}, instance_id: {instance_id}"
                )
                volume.detach_from_instance(
                    Device=device,
                    InstanceId=instance_id,
                )

            # delete volume
            volume.delete()
            print_info(f"Secret deleted: {self.name}")
            return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be deleted.")
            print_error("Please try again or delete resources manually.")
            print_error(e)
        return False

    def get_volume_id(
        self,
        aws_client: Optional[AwsApiClient] = None,
        aws_region: Optional[str] = None,
        aws_profile: Optional[str] = None,
    ) -> Optional[str]:
        aws_api_client = aws_client or AwsApiClient(
            aws_region=aws_region, aws_profile=aws_profile
        )
        if aws_api_client is not None:
            self._read(aws_api_client)
        return self.volume_id

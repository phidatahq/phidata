from pathlib import Path
from typing import Optional, Any, Dict, List, Union

from phidata.aws.api_client import AwsApiClient
from phidata.aws.resource.base import AwsResource
from phidata.utils.cli_console import print_info, print_error
from phidata.utils.log import logger

import json


class SecretsManager(AwsResource):
    """
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/secretsmanager.html
    """

    resource_type = "SecretsManager"
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

    # Read secret key/value pairs from yaml files
    secret_files: Optional[List[Path]] = None
    # Read secret key/value pairs from yaml files in a directory
    secrets_dir: Optional[Path] = None
    # Force delete the secret without recovery
    force_delete: Optional[bool] = True

    # provided by api on create
    secret_arn: Optional[str] = None
    secret_resource_name: Optional[str] = None
    secret_value: Optional[dict] = None

    def _create(self, aws_client: AwsApiClient) -> bool:
        """Creates the SecretsManager

        Args:
            aws_client: The AwsApiClient for the current secret
        """
        print_info(f"Creating {self.get_resource_type()}: {self.get_resource_name()}")

        # Step 1: Read secrets from files
        secret_dict: Dict[str, Any] = {}
        if self.secret_files:
            for f in self.secret_files:
                _s = self.read_yaml_file(f)
                if _s:
                    secret_dict.update(_s)
        if self.secrets_dir:
            for f in self.secrets_dir.glob("*.yaml"):
                _s = self.read_yaml_file(f)
                if _s:
                    secret_dict.update(_s)
            for f in self.secrets_dir.glob("*.yml"):
                _s = self.read_yaml_file(f)
                if _s:
                    secret_dict.update(_s)

        secret_string = self.secret_string
        if secret_dict:
            if secret_string:
                secret_dict.update(json.loads(secret_string))

            secret_string = json.dumps(secret_dict)
            logger.debug(f"secret_string: {secret_string}")

        # Step 2: Build SecretsManager configuration
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
        if secret_string:
            not_null_args["SecretString"] = secret_string
        if self.tags:
            not_null_args["Tags"] = self.tags
        if self.add_replica_regions:
            not_null_args["AddReplicaRegions"] = self.add_replica_regions
        if self.force_overwrite_replica_secret:
            not_null_args[
                "ForceOverwriteReplicaSecret"
            ] = self.force_overwrite_replica_secret

        # Step 3: Create SecretsManager
        service_client = self.get_service_client(aws_client)
        try:
            created_resource = service_client.create_secret(
                Name=self.name,
                **not_null_args,
            )
            logger.debug(f"SecretsManager: {created_resource}")

            # Validate SecretsManager creation
            self.secret_arn = created_resource.get("ARN", None)
            self.secret_resource_name = created_resource.get("Name", None)
            logger.debug(f"secret_arn: {self.secret_arn}")
            logger.debug(f"secret_resource_name: {self.secret_resource_name}")
            if self.secret_arn is not None:
                print_info(f"SecretsManager created: {self.name}")
                self.active_resource = created_resource
                self.save_resource_file()
                return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be created.")
            print_error(e)
        return False

    def _read(self, aws_client: AwsApiClient) -> Optional[Any]:
        """Returns the SecretsManager

        Args:
            aws_client: The AwsApiClient for the current secret
        """
        logger.debug(f"Reading {self.get_resource_type()}: {self.get_resource_name()}")

        from botocore.exceptions import ClientError

        service_client = self.get_service_client(aws_client)
        try:
            describe_response = service_client.describe_secret(SecretId=self.name)
            logger.debug(f"SecretsManager: {describe_response}")

            self.secret_arn = describe_response.get("ARN", None)
            self.secret_resource_name = describe_response.get("Name", None)
            secret_deleted_date = describe_response.get("DeletedDate", None)
            logger.debug(f"secret_arn: {self.secret_arn}")
            logger.debug(f"secret_resource_name: {self.secret_resource_name}")
            logger.debug(f"secret_deleted_date: {secret_deleted_date}")
            if self.secret_arn is not None:
                print_info(f"SecretsManager available: {self.name}")
                self.active_resource = describe_response
                self.save_resource_file()
        except ClientError as ce:
            logger.debug(f"ClientError: {ce}")
        except Exception as e:
            print_error(f"Error reading {self.get_resource_type()}.")
            print_error(e)
        return self.active_resource

    def _delete(self, aws_client: AwsApiClient) -> bool:
        """Deletes the SecretsManager

        Args:
            aws_client: The AwsApiClient for the current secret
        """
        print_info(f"Deleting {self.get_resource_type()}: {self.get_resource_name()}")

        service_client = self.get_service_client(aws_client)
        self.active_resource = None
        self.secret_value = None
        try:
            delete_response = service_client.delete_secret(
                SecretId=self.name, ForceDeleteWithoutRecovery=self.force_delete
            )
            logger.debug(f"SecretsManager: {delete_response}")
            print_info(
                f"{self.get_resource_type()}: {self.get_resource_name()} deleted"
            )
            self.save_resource_file()
            return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be deleted.")
            print_error("Please try again or delete resources manually.")
            print_error(e)
        return False

    def get_secret_dict(self, aws_client: Optional[AwsApiClient] = None) -> Any:
        """Get secret value

        Args:
            aws_client: The AwsApiClient for the current secret
        """
        logger.debug(f"Getting {self.get_resource_type()}: {self.get_resource_name()}")

        from botocore.exceptions import ClientError

        client: AwsApiClient = aws_client or self.get_aws_client()
        service_client = self.get_service_client(client)
        try:
            secret_value = service_client.get_secret_value(SecretId=self.name)
            logger.debug(f"SecretsManager: {secret_value}")

            if secret_value is None:
                logger.warning(f"SecretsManager is None: {self.name}")
                return None

            self.secret_value = secret_value
            self.secret_arn = secret_value.get("ARN", None)
            self.secret_resource_name = secret_value.get("Name", None)
            self.save_resource_file()

            secret_string = secret_value.get("SecretString", None)
            if secret_string is not None:
                return json.loads(secret_string)

            secret_binary = secret_value.get("SecretBinary", None)
            if secret_binary is not None:
                return secret_binary
        except ClientError as ce:
            logger.debug(f"ClientError: {ce}")
        except Exception as e:
            print_error(f"Error reading {self.get_resource_type()}.")
            print_error(e)
        return None

    def _update(self, aws_client: AwsApiClient) -> bool:
        """Update SecretsManager"""
        print_info(f"Updating {self.get_resource_type()}: {self.get_resource_name()}")

        # Step 1: Read secrets from files
        local_secrets: Dict[str, Any] = {}
        if self.secret_files:
            for f in self.secret_files:
                _s = self.read_yaml_file(f)
                if _s:
                    local_secrets.update(_s)
        if self.secrets_dir:
            for f in self.secrets_dir.glob("*.yaml"):
                _s = self.read_yaml_file(f)
                if _s:
                    local_secrets.update(_s)
            for f in self.secrets_dir.glob("*.yml"):
                _s = self.read_yaml_file(f)
                if _s:
                    local_secrets.update(_s)

        secret_string = self.secret_string
        if local_secrets:
            if secret_string:
                local_secrets.update(json.loads(secret_string))

            secret_string = json.dumps(local_secrets)
            logger.debug(f"Local secrets: {secret_string}")

        # Step 2: Read secrets from AWS SecretsManager
        aws_secrets = self.get_secret_dict()
        logger.debug(f"AWS secrets: {aws_secrets}")

        if local_secrets and aws_secrets:
            all_secrets = json.dumps(local_secrets | aws_secrets)
        elif local_secrets:
            all_secrets = json.dumps(secret_string)
        elif aws_secrets:
            all_secrets = json.dumps(aws_secrets)

        logger.debug(f"All secrets: {all_secrets}")

        # Step 3: Update AWS SecretsManager
        service_client = self.get_service_client(aws_client)
        self.active_resource = None
        self.secret_value = None
        try:
            create_response = service_client.update_secret(
                SecretId=self.name,
                SecretString=all_secrets,
            )
            logger.debug(f"SecretsManager: {create_response}")
            print_info(
                f"{self.get_resource_type()}: {self.get_resource_name()} Updated"
            )
            self.save_resource_file()
            return True
        except Exception as e:
            print_error(f"{self.get_resource_type()} could not be Updated.")
            print_error(e)
        return False

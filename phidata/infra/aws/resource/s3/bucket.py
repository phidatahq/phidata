from typing import Optional, Any
from typing_extensions import Literal

from botocore.exceptions import ClientError

from phidata.infra.aws.api_client import AwsApiClient
from phidata.infra.aws.resource.base import AwsResource
from phidata.utils.cli_console import print_info, print_error
from phidata.utils.log import logger


class S3Bucket(AwsResource):
    """
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#service-resource
    """

    resource_type = "s3.Bucket"
    service_name = "s3"

    # name of bucket
    name: str
    # The canned ACL to apply to the bucket.
    acl: Optional[
        Literal["private", "public-read", "public-read-write", "authenticated-read"]
    ] = None
    grant_full_control: Optional[str] = None
    grant_read: Optional[str] = None
    grant_read_ACP: Optional[str] = None
    grant_write: Optional[str] = None
    grant_write_ACP: Optional[str] = None
    object_lock_enabled_for_bucket: Optional[bool] = None
    object_ownership: Optional[
        Literal["BucketOwnerPreferred", "ObjectWriter", "BucketOwnerEnforced"]
    ] = None

    skip_delete = True

    def _create(self, aws_client: AwsApiClient) -> bool:
        """Creates the s3.Bucket

        Args:
            aws_client: The AwsApiClient for the current cluster
        """

        print_info(f"Creating {self.get_resource_type()}: {self.get_resource_name()}")
        try:
            service_resource = self.get_service_resource(aws_client)

            ## Create Bucket
            # Bucket names are GLOBALLY unique!
            # AWS will give you the IllegalLocationConstraintException if you collide
            # with an already existing bucket and you've specified a region different than
            # the region of the already existing bucket. If you happen to guess the correct region of the
            # existing bucket it will give you the BucketAlreadyExists exception.
            bucket_configuration = {}
            if aws_client.aws_region != "us-east-1":
                bucket_configuration["LocationConstraint"] = aws_client.aws_region
            bucket = service_resource.create_bucket(
                Bucket=self.name,
                # CreateBucketConfiguration=bucket_configuration,
                ACL=self.acl if self.acl is not None else "",
                # GrantFullControl=self.grant_full_control,
                # GrantRead=self.grant_read,
                # GrantReadACP=self.grant_read_ACP,
                # GrantWrite=self.grant_write,
                # GrantWriteACP=self.grant_write_ACP,
                # ObjectLockEnabledForBucket=self.object_lock_enabled_for_bucket,
                # ObjectOwnership=self.object_ownership,
            )
            # logger.debug(f"Bucket: {bucket}")
            # logger.debug(f"Bucket type: {type(bucket)}")

            ## Validate Bucket creation
            bucket.load()
            creation_date = bucket.creation_date
            logger.debug(f"creation_date: {creation_date}")
            if creation_date is not None:
                print_info(f"Bucket created: {bucket.name}")
                self.active_resource = bucket
                self.active_resource_class = bucket.__class__
                return True
            logger.error("Bucket could not be created")
        except Exception as e:
            logger.exception(e)
        return False

    def post_create(self, aws_client: AwsApiClient) -> bool:
        ## Wait for Bucket to be created
        if self.wait_for_creation:
            try:
                print_info("Waiting for Bucket to be created")
                waiter = self.get_service_client(aws_client).get_waiter("bucket_exists")
                waiter.wait(
                    Bucket=self.name,
                    WaiterConfig={
                        "Delay": self.waiter_delay,
                        "MaxAttempts": self.waiter_max_attempts,
                    },
                )
            except Exception as e:
                print_error(
                    f"Waiter Bucket Stack {self.name} failed, downstream actions might fail."
                )
                print_error(e)
                print_error("---+---")
        return True

    def _read(self, aws_client: AwsApiClient) -> Optional[Any]:
        """Returns the s3.Bucket

        Args:
            aws_client: The AwsApiClient for the current cluster
        """
        logger.debug(f"Reading {self.get_resource_type()}: {self.get_resource_name()}")
        try:
            service_resource = self.get_service_resource(aws_client)
            bucket = service_resource.Bucket(name=self.name)

            bucket.load()
            creation_date = bucket.creation_date
            logger.debug(f"Bucket creation_date: {creation_date}")
            if creation_date is not None:
                logger.debug(f"Bucket found: {bucket.name}")
                self.active_resource = bucket
                self.active_resource_class = bucket.__class__
        except ClientError as ce:
            logger.debug(f"ClientError: {ce}")
            pass
        except Exception as e:
            logger.exception(e)
        return self.active_resource

    def _delete(self, aws_client: AwsApiClient) -> bool:
        """Deletes the s3.Bucket

        Args:
            aws_client: The AwsApiClient for the current cluster
        """

        print_info(f"Deleting {self.get_resource_type()}: {self.get_resource_name()}")
        try:
            bucket = self.read(aws_client)
            # logger.debug(f"Bucket: {bucket}")
            # logger.debug(f"Bucket type: {type(bucket)}")
            self.active_resource = None
            self.active_resource_class = None
            bucket.delete()
            print_info(f"Bucket deleted: {bucket}")
            return True
        except Exception as e:
            logger.exception(e)
        return False

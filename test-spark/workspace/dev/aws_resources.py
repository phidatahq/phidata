from phidata.aws.config import AwsResourceGroup
from phidata.aws.resource.s3.bucket import S3Bucket

from workspace.settings import ws_settings

#
# -*- AWS resources
#

# -*- Settings
# Do not create the resource when running `phi ws up`
skip_create: bool = False
# Do not delete the resource when running `phi ws down`
skip_delete: bool = False
# Wait for the resource to be created
wait_for_create: bool = True
# Wait for the resource to be deleted
wait_for_delete: bool = True

# -*- S3 buckets
# S3 bucket for storing logs
dev_logs_s3_bucket = S3Bucket(
    name=f"{ws_settings.dev_key}-logs",
    acl="private",
    skip_create=skip_create,
    skip_delete=skip_delete,
    wait_for_creation=wait_for_create,
    wait_for_deletion=wait_for_delete,
)

# S3 bucket for storing data
dev_data_s3_bucket = S3Bucket(
    name=f"{ws_settings.dev_key}-data",
    acl="private",
    skip_create=skip_create,
    skip_delete=skip_delete,
    wait_for_creation=wait_for_create,
    wait_for_deletion=wait_for_delete,
)

dev_aws_resources = AwsResourceGroup(
    name=ws_settings.dev_key,
    s3_buckets=[dev_logs_s3_bucket, dev_data_s3_bucket],
)

from typing import Any, Optional

from pydantic import Field

from phi.aws.api_client import AwsApiClient
from phi.aws.resource.base import AwsResource


class S3Object(AwsResource):
    """
    Reference:
    - https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/object/index.html
    """

    resource_type: str = "s3"
    service_name: str = "s3"

    # The Object’s bucket_name identifier. This must be set.
    bucket_name: str
    # The Object’s key identifier. This must be set.
    name: str = Field(..., alias="key")

    @property
    def uri(self) -> str:
        """Returns the URI of the s3.Object

        Returns:
            str: The URI of the s3.Object
        """
        return f"s3://{self.bucket_name}/{self.name}"

    def get_resource(self, aws_client: Optional[AwsApiClient] = None) -> Any:
        """Returns the s3.Object

        Args:
            aws_client: The AwsApiClient for the current cluster

        Returns:
            The s3.Object
        """
        client: AwsApiClient = aws_client or self.get_aws_client()
        service_resource = self.get_service_resource(client)
        return service_resource.Object(
            bucket_name=self.bucket_name,
            key=self.name,
        )

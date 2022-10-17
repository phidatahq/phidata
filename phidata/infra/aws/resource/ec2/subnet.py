from typing import Optional

from phidata.infra.aws.api_client import AwsApiClient
from phidata.infra.aws.resource.base import AwsResource
from phidata.utils.cli_console import print_error
from phidata.utils.log import logger


class Subnet(AwsResource):
    """
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#subnet
    """

    resource_type = "Subnet"
    service_name = "ec2"

    # Subnet id
    id: str

    def get_resource_name(self) -> Optional[str]:
        return self.id

    def get_availability_zone(
        self, aws_client: Optional[AwsApiClient] = None
    ) -> Optional[str]:
        # logger.debug(f"Reading {self.get_resource_type()}: {self.get_resource_name()}")

        from botocore.exceptions import ClientError

        client: AwsApiClient = aws_client or self.get_aws_client()
        service_resource = self.get_service_resource(client)
        try:
            subnet = service_resource.Subnet(self.id)
            az = subnet.availability_zone
            logger.debug(f"AZ for {self.id}: {az}")
            return az
        except ClientError as ce:
            logger.debug(f"ClientError: {ce}")
        except Exception as e:
            print_error(f"Error reading {self.get_resource_type()}: {e}")
        return None

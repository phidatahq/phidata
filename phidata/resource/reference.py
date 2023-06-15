from typing import Optional
from phidata.aws.api_client import AwsApiClient


class Reference:
    def __init__(self, reference):
        self.reference = reference

    def get_reference(self):
        return self.reference()


class AwsReference:
    def __init__(self, reference):
        self.reference = reference

    def get_reference(self, aws_client: Optional[AwsApiClient] = None):
        return self.reference(aws_client=aws_client)

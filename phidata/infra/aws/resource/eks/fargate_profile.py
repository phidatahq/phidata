from typing import Optional, Any, Dict, List
from textwrap import dedent

from phidata.infra.aws.api_client import AwsApiClient
from phidata.infra.aws.resource.base import AwsResource
from phidata.infra.aws.resource.cloudformation.stack import CloudFormationStack
from phidata.infra.aws.resource.eks.cluster import EksCluster
from phidata.infra.aws.resource.iam.role import IamRole
from phidata.utils.cli_console import print_info, print_error
from phidata.utils.log import logger


class EksFargateProfile(AwsResource):
    """
    The Fargate profile allows an administrator to declare which pods run on Fargate and specify which pods
    run on which Fargate profile. This declaration is done through the profile’s selectors.
    Each profile can have up to five selectors that contain a namespace and labels.
    A namespace is required for every selector. The label field consists of multiple optional key-value pairs.
    Pods that match the selectors are scheduled on Fargate.
    If a to-be-scheduled pod matches any of the selectors in the Fargate profile, then that pod is run on Fargate.

    fargate_role:
    When you create a Fargate profile, you must specify a pod execution role to use with the pods that are scheduled
    with the profile. This role is added to the cluster's Kubernetes Role Based Access Control (RBAC) for
    authorization so that the kubelet that is running on the Fargate infrastructure can register with your
    Amazon EKS cluster so that it can appear in your cluster as a node. The pod execution role also provides
    IAM permissions to the Fargate infrastructure to allow read access to Amazon ECR image repositories.

    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/eks.html
    """

    resource_type = "EksFargateProfile"
    service_name = "eks"

    # Name for the fargate profile
    name: str
    # The cluster to create the EksFargateProfile in
    eks_cluster: EksCluster

    # If role is None, a default fargate_role is created using fargate_role_name
    fargate_role: Optional[IamRole] = None
    # Name for the default fargate_role when role is None, use "name-iam-role" if not provided
    fargate_role_name: Optional[str] = None

    # The Kubernetes namespace that the selector should match.
    namespace: str = "default"
    # The Kubernetes labels that the selector should match.
    # A pod must contain all of the labels that are specified in the selector for it to be considered a match.
    labels: Optional[Dict[str, str]] = None
    # Unique, case-sensitive identifier that you provide to ensure the idempotency of the request.
    # This field is autopopulated if not provided.
    client_request_token: Optional[str] = None
    # The metadata to apply to the Fargate profile to assist with categorization and organization.
    # Each tag consists of a key and an optional value. You define both.
    tags: Optional[Dict[str, str]] = None

    skip_delete = False
    # bump the wait time for Eks to 30 seconds
    waiter_delay = 30

    def _create(self, aws_client: AwsApiClient) -> bool:
        """Creates a Fargate profile for your Amazon EKS cluster.

        Args:
            aws_client: The AwsApiClient for the current cluster
        """

        print_info(f"Creating {self.get_resource_type()}: {self.get_resource_name()}")
        try:
            # Create the Fargate IamRole if needed
            fargate_iam_role = self.get_fargate_iam_role()
            try:
                print_info(f"Creating IamRole: {fargate_iam_role.name}")
                fargate_iam_role.create(aws_client)
                fargate_iam_role_arn = fargate_iam_role.read(aws_client).arn
                print_info(f"fargate_iam_role_arn: {fargate_iam_role_arn}")
            except Exception as e:
                print_error("IamRole creation failed, please try again")
                print_error(e)
                return False

            # Get private subnets
            # Only private subnets are supported for pods that are running on Fargate.
            eks_vpc_stack: CloudFormationStack = self.eks_cluster.get_eks_vpc_stack()
            private_subnets: Optional[List[str]] = eks_vpc_stack.get_private_subnets(
                aws_client
            )

            # create a dict of args which are not null, otherwise aws type validation fails
            not_null_args: Dict[str, Any] = {}
            if private_subnets is not None:
                not_null_args["subnets"] = private_subnets

            default_selector: Dict[str, Any] = {
                "namespace": self.namespace,
            }
            if self.labels is not None:
                default_selector["labels"] = self.labels
            if self.client_request_token:
                not_null_args["clientRequestToken"] = self.client_request_token
            if self.tags:
                not_null_args["tags"] = self.tags

            ## Create a Fargate profile
            # Get the service_client
            service_client = self.get_service_client(aws_client)
            # logger.debug(f"ServiceClient: {service_client}")
            # logger.debug(f"ServiceClient type: {type(service_client)}")
            try:
                print_info(f"Creating EksFargateProfile: {self.name}")
                create_profile_response = service_client.create_fargate_profile(
                    fargateProfileName=self.name,
                    clusterName=self.eks_cluster.name,
                    podExecutionRoleArn=fargate_iam_role_arn,
                    selectors=[default_selector],
                    **not_null_args,
                )
                # logger.debug(f"create_profile_response: {create_profile_response}")
                # logger.debug(
                #     f"create_profile_response type: {type(create_profile_response)}"
                # )
                ## Validate Fargate role creation
                fargate_profile_creation_time = create_profile_response.get(
                    "fargateProfile", {}
                ).get("createdAt", None)
                fargate_profile_status = create_profile_response.get(
                    "fargateProfile", {}
                ).get("status", None)
                logger.debug(f"creation_time: {fargate_profile_creation_time}")
                logger.debug(f"cluster_status: {fargate_profile_status}")
                if fargate_profile_creation_time is not None:
                    print_info(f"EksFargateProfile created: {self.name}")
                    self.active_resource = create_profile_response
                    self.active_resource_class = create_profile_response.__class__
                    return True
            except Exception as e:
                print_error(
                    "EksFargateProfile could not be created, this operation is known to be buggy."
                )
                print_error("Please deploy the workspace again.")
                print_error(e)
                return False
        except Exception as e:
            print_error(e)
        return False

    def post_create(self, aws_client: AwsApiClient) -> bool:
        ## Wait for EksFargateProfile to be created
        if self.wait_for_creation:
            try:
                print_info(
                    "Waiting for EksFargateProfile to be created, this can take upto 5 minutes"
                )
                waiter = self.get_service_client(aws_client).get_waiter(
                    "fargate_profile_active"
                )
                waiter.wait(
                    clusterName=self.eks_cluster.name,
                    fargateProfileName=self.name,
                    WaiterConfig={
                        "Delay": self.waiter_delay,
                        "MaxAttempts": self.waiter_max_attempts,
                    },
                )
            except Exception as e:
                print_error(
                    "Received errors while waiting for EksFargateProfile creation, this operation is known to be buggy."
                )
                print_error(e)
                return False
        return True

    def _read(self, aws_client: AwsApiClient) -> Optional[Any]:
        """Returns the EksFargateProfile

        Args:
            aws_client: The AwsApiClient for the current cluster
        """
        from botocore.exceptions import ClientError

        logger.debug(f"Reading {self.get_resource_type()}: {self.get_resource_name()}")
        try:
            service_client = self.get_service_client(aws_client)
            describe_profile_response = service_client.describe_fargate_profile(
                clusterName=self.eks_cluster.name,
                fargateProfileName=self.name,
            )
            # logger.debug(f"describe_profile_response: {describe_profile_response}")
            # logger.debug(f"describe_profile_response type: {type(describe_profile_response)}")

            fargate_profile_creation_time = describe_profile_response.get(
                "fargateProfile", {}
            ).get("createdAt", None)
            fargate_profile_status = describe_profile_response.get(
                "fargateProfile", {}
            ).get("status", None)
            logger.debug(
                f"FargateProfile creation_time: {fargate_profile_creation_time}"
            )
            logger.debug(f"FargateProfile status: {fargate_profile_status}")
            if fargate_profile_creation_time is not None:
                logger.debug(f"EksFargateProfile found: {self.name}")
                self.active_resource = describe_profile_response
                self.active_resource_class = describe_profile_response.__class__
        except ClientError as ce:
            logger.debug(f"ClientError: {ce}")
        except Exception as e:
            logger.error(e)
        return self.active_resource

    def _delete(self, aws_client: AwsApiClient) -> bool:
        """Deletes the EksFargateProfile

        Args:
            aws_client: The AwsApiClient for the current cluster
        """

        print_info(f"Deleting {self.get_resource_type()}: {self.get_resource_name()}")
        try:
            # Create the Fargate IamRole
            fargate_iam_role = self.get_fargate_iam_role()
            try:
                print_info(f"Deleting IamRole: {fargate_iam_role.name}")
                fargate_iam_role.delete(aws_client)
            except Exception as e:
                print_error(
                    "IamRole deletion failed, please try again or delete manually"
                )
                print_error(e)

            # Delete the Fargate profile
            service_client = self.get_service_client(aws_client)
            self.active_resource = None
            self.active_resource_class = None
            delete_profile_response = service_client.delete_fargate_profile(
                clusterName=self.eks_cluster.name,
                fargateProfileName=self.name,
            )
            # logger.debug(f"delete_profile_response: {delete_profile_response}")
            # logger.debug(
            #     f"delete_profile_response type: {type(delete_profile_response)}"
            # )
            print_info(f"EksFargateProfile deleted: {self.name}")
            return True

        except Exception as e:
            logger.error(e)
        return False

    def post_delete(self, aws_client: AwsApiClient) -> bool:
        ## Wait for EksFargateProfile to be deleted
        if self.wait_for_deletion:
            try:
                print_info(
                    "Waiting for EksFargateProfile to be deleted, this can take upto 5 minutes"
                )
                waiter = self.get_service_client(aws_client).get_waiter(
                    "fargate_profile_deleted"
                )
                waiter.wait(
                    clusterName=self.eks_cluster.name,
                    fargateProfileName=self.name,
                    WaiterConfig={
                        "Delay": self.waiter_delay,
                        "MaxAttempts": self.waiter_max_attempts,
                    },
                )
                return True
            except Exception as e:
                print_error(
                    "Received errors while waiting for EksFargateProfile deletion, this operation is known to be buggy."
                )
                print_error("Please try again or delete resources manually.")
                print_error(e)
        return True

    def get_fargate_iam_role(self) -> IamRole:
        """
        Create an IAM role and attach the required Amazon EKS IAM managed policy to it.
        When your cluster creates pods on Fargate infrastructure, the components running on the Fargate
        infrastructure need to make calls to AWS APIs on your behalf to do things like pull
        container images from Amazon ECR or route logs to other AWS services.
        The Amazon EKS pod execution role provides the IAM permissions to do this.
        Returns:

        """
        if self.fargate_role is not None:
            return self.fargate_role
        return IamRole(
            name=self.fargate_role_name or f"{self.name}-iam-role",
            assume_role_policy_document=dedent(
                """\
            {
              "Version": "2012-10-17",
              "Statement": [
                {
                  "Effect": "Allow",
                  "Principal": {
                    "Service": "eks-fargate-pods.amazonaws.com"
                  },
                  "Action": "sts:AssumeRole"
                }
              ]
            }
            """
            ),
            policy_arns=[
                "arn:aws:iam::aws:policy/AmazonEKSFargatePodExecutionRolePolicy"
            ],
        )

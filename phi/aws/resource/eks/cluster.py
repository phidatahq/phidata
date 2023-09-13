from pathlib import Path
from textwrap import dedent
from typing import Optional, Any, Dict, List, Union

from phi.aws.api_client import AwsApiClient
from phi.aws.resource.base import AwsResource
from phi.aws.resource.iam.role import IamRole
from phi.aws.resource.cloudformation.stack import CloudFormationStack
from phi.aws.resource.ec2.subnet import Subnet
from phi.aws.resource.eks.addon import EksAddon
from phi.cli.console import print_info
from phi.utils.log import logger


class EksCluster(AwsResource):
    """
    Reference:
    - https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/eks.html
    """

    resource_type: Optional[str] = "EksCluster"
    service_name: str = "eks"

    # The unique name to give to your cluster.
    name: str
    # version: The desired Kubernetes version for your cluster.
    # If you don't specify a value here, the latest version available in Amazon EKS is used.
    version: Optional[str] = None

    # role: The IAM role that provides permissions for the Kubernetes control plane to make calls
    # to Amazon Web Services API operations on your behalf.
    # ARN for the EKS IAM role to use
    role_arn: Optional[str] = None
    # If role_arn is None, a default role is created if create_role is True
    create_role: bool = True
    # Provide IamRole to create or use default of role is None
    role: Optional[IamRole] = None
    # Name for the default role when role is None, use "name-role" if not provided
    role_name: Optional[str] = None
    # Provide a list of policy ARNs to attach to the role
    add_policy_arns: Optional[List[str]] = None

    # EKS VPC Configuration
    # resources_vpc_config: The VPC configuration that's used by the cluster control plane.
    # Amazon EKS VPC resources have specific requirements to work properly with Kubernetes.
    # You must specify at least two subnets. You can specify up to five security groups.
    resources_vpc_config: Optional[Dict[str, Any]] = None
    # If resources_vpc_config is None, a default CloudFormationStack is created if create_vpc_stack is True
    create_vpc_stack: bool = True
    # The CloudFormationStack to build resources_vpc_config if provided
    vpc_stack: Optional[CloudFormationStack] = None
    # If resources_vpc_config and vpc_stack are None
    # create a default CloudFormationStack using vpc_stack_name, use "name-vpc-stack" if vpc_stack_name is None
    vpc_stack_name: Optional[str] = None
    # Default VPC Stack Template URL
    vpc_stack_template_url: str = (
        "https://s3.us-west-2.amazonaws.com/amazon-eks/cloudformation/2020-10-29/amazon-eks-vpc-private-subnets.yaml"
    )
    use_public_subnets: bool = True
    use_private_subnets: bool = True
    subnet_az: Optional[Union[str, List[str]]] = None
    add_subnets: Optional[List[str]] = None
    add_security_groups: Optional[List[str]] = None
    endpoint_public_access: Optional[bool] = None
    endpoint_private_access: Optional[bool] = None
    public_access_cidrs: Optional[List[str]] = None

    # The Kubernetes network configuration for the cluster.
    kubernetes_network_config: Optional[Dict[str, str]] = None
    # Enable or disable exporting the Kubernetes control plane logs for your cluster to CloudWatch Logs.
    # By default, cluster control plane logs aren't exported to CloudWatch Logs.
    logging: Optional[Dict[str, List[dict]]] = None
    # Unique, case-sensitive identifier that you provide to ensure the idempotency of the request.
    client_request_token: Optional[str] = None
    # The metadata to apply to the cluster to assist with categorization and organization.
    # Each tag consists of a key and an optional value. You define both.
    tags: Optional[Dict[str, str]] = None
    # The encryption configuration for the cluster.
    encryption_config: Optional[List[Dict[str, Union[List[str], Dict[str, str]]]]] = None

    # EKS Addons
    addons: List[Union[str, EksAddon]] = ["aws-ebs-csi-driver", "aws-efs-csi-driver", "vpc-cni", "coredns"]

    # Kubeconfig
    # If True, updates the kubeconfig on create/delete
    # Use manage_kubeconfig = False when using a separate EksKubeconfig resource
    manage_kubeconfig: bool = True
    # The kubeconfig_path to update
    kubeconfig_path: Path = Path.home().joinpath(".kube").joinpath("config").resolve()
    # Optional: cluster_name to use in kubeconfig, defaults to self.name
    kubeconfig_cluster_name: Optional[str] = None
    # Optional: cluster_user to use in kubeconfig, defaults to self.name
    kubeconfig_cluster_user: Optional[str] = None
    # Optional: cluster_context to use in kubeconfig, defaults to self.name
    kubeconfig_cluster_context: Optional[str] = None
    # Optional: role to assume when signing the token
    kubeconfig_role: Optional[IamRole] = None
    # Optional: role arn to assume when signing the token
    kubeconfig_role_arn: Optional[str] = None

    # provided by api on create
    created_at: Optional[str] = None
    cluster_status: Optional[str] = None

    # bump the wait time for Eks to 30 seconds
    waiter_delay: int = 30

    def _create(self, aws_client: AwsApiClient) -> bool:
        """Creates the EksCluster

        Args:
            aws_client: The AwsApiClient for the current cluster
        """
        print_info(f"Creating {self.get_resource_type()}: {self.get_resource_name()}")

        # Step 1: Get IamRoleArn
        eks_iam_role_arn = self.role_arn
        if eks_iam_role_arn is None and self.create_role:
            # Create the IamRole and get eks_iam_role_arn
            eks_iam_role = self.get_eks_iam_role()
            try:
                eks_iam_role.create(aws_client)
                eks_iam_role_arn = eks_iam_role.read(aws_client).arn
                print_info(f"ARN for {eks_iam_role.name}: {eks_iam_role_arn}")
            except Exception as e:
                logger.error("IamRole creation failed, please fix and try again")
                logger.error(e)
                return False
        if eks_iam_role_arn is None:
            logger.error("IamRole ARN not available, please fix and try again")
            return False

        # Step 2: Get the VPC config
        resources_vpc_config = self.resources_vpc_config
        if resources_vpc_config is None and self.create_vpc_stack:
            print_info("Creating default vpc stack as no resources_vpc_config provided")
            # Create the CloudFormationStack and get resources_vpc_config
            vpc_stack = self.get_vpc_stack()
            try:
                vpc_stack.create(aws_client)
                resources_vpc_config = self.get_eks_resources_vpc_config(aws_client, vpc_stack)
            except Exception as e:
                logger.error("Stack creation failed, please fix and try again")
                logger.error(e)
                return False
        if resources_vpc_config is None:
            logger.error("VPC configuration not available, please fix and try again")
            return False

        # create a dict of args which are not null, otherwise aws type validation fails
        not_null_args: Dict[str, Any] = {}
        if self.version:
            not_null_args["version"] = self.version
        if self.kubernetes_network_config:
            not_null_args["kubernetesNetworkConfig"] = self.kubernetes_network_config
        if self.logging:
            not_null_args["logging"] = self.logging
        if self.client_request_token:
            not_null_args["clientRequestToken"] = self.client_request_token
        if self.tags:
            not_null_args["tags"] = self.tags
        if self.encryption_config:
            not_null_args["encryptionConfig"] = self.encryption_config

        # Step 3: Create EksCluster
        service_client = self.get_service_client(aws_client)
        try:
            create_response = service_client.create_cluster(
                name=self.name,
                roleArn=eks_iam_role_arn,
                resourcesVpcConfig=resources_vpc_config,
                **not_null_args,
            )
            logger.debug(f"EksCluster: {create_response}")
            cluster_dict = create_response.get("cluster", {})

            # Validate Cluster creation
            self.created_at = cluster_dict.get("createdAt", None)
            self.cluster_status = cluster_dict.get("status", None)
            logger.debug(f"created_at: {self.created_at}")
            logger.debug(f"cluster_status: {self.cluster_status}")
            if self.created_at is not None:
                print_info(f"EksCluster created: {self.name}")
                self.active_resource = create_response
                return True
        except Exception as e:
            logger.error(f"{self.get_resource_type()} could not be created.")
            logger.error(e)
        return False

    def post_create(self, aws_client: AwsApiClient) -> bool:
        # Wait for Cluster to be created
        if self.wait_for_create:
            try:
                print_info(f"Waiting for {self.get_resource_type()} to be active.")
                waiter = self.get_service_client(aws_client).get_waiter("cluster_active")
                waiter.wait(
                    name=self.name,
                    WaiterConfig={
                        "Delay": self.waiter_delay,
                        "MaxAttempts": self.waiter_max_attempts,
                    },
                )
            except Exception as e:
                logger.error("Waiter failed.")
                logger.error(e)

        # Add addons
        if self.addons is not None:
            addons_created: List[EksAddon] = []
            for _addon in self.addons:
                addon_to_create: Optional[EksAddon] = None
                if isinstance(_addon, EksAddon):
                    addon_to_create = _addon
                elif isinstance(_addon, str):
                    addon_to_create = EksAddon(name=_addon, cluster_name=self.name)

                if addon_to_create is not None:
                    addon_success = addon_to_create._create(aws_client)  # type: ignore
                    if addon_success:
                        addons_created.append(addon_to_create)

            # Wait for Addons to be created
            if self.wait_for_create:
                for addon in addons_created:
                    addon.post_create(aws_client)

        # Update kubeconfig if needed
        if self.manage_kubeconfig:
            self.write_kubeconfig(aws_client=aws_client)
        return True

    def _read(self, aws_client: AwsApiClient) -> Optional[Any]:
        """Returns the EksCluster

        Args:
            aws_client: The AwsApiClient for the current cluster
        """
        logger.debug(f"Reading {self.get_resource_type()}: {self.get_resource_name()}")

        from botocore.exceptions import ClientError

        service_client = self.get_service_client(aws_client)
        try:
            describe_response = service_client.describe_cluster(name=self.name)
            # logger.debug(f"EksCluster: {describe_response}")
            cluster_dict = describe_response.get("cluster", {})

            self.created_at = cluster_dict.get("createdAt", None)
            self.cluster_status = cluster_dict.get("status", None)
            logger.debug(f"EksCluster created_at: {self.created_at}")
            logger.debug(f"EksCluster status: {self.cluster_status}")
            if self.created_at is not None:
                logger.debug(f"EksCluster found: {self.name}")
                self.active_resource = describe_response
        except ClientError as ce:
            logger.debug(f"ClientError: {ce}")
        except Exception as e:
            logger.error(f"Error reading {self.get_resource_type()}.")
            logger.error(e)
        return self.active_resource

    def _delete(self, aws_client: AwsApiClient) -> bool:
        """Deletes the EksCluster
        Deletes the Amazon EKS cluster control plane.
        If you have active services in your cluster that are associated with a load balancer,
        you must delete those services before deleting the cluster so that the load balancers
        are deleted properly. Otherwise, you can have orphaned resources in your VPC
        that prevent you from being able to delete the VPC.

        Args:
            aws_client: The AwsApiClient for the current cluster
        """
        print_info(f"Deleting {self.get_resource_type()}: {self.get_resource_name()}")

        # Step 1: Delete the IamRole
        if self.role_arn is None and self.create_role:
            eks_iam_role = self.get_eks_iam_role()
            try:
                eks_iam_role.delete(aws_client)
            except Exception as e:
                logger.error("IamRole deletion failed, please try again or delete manually")
                logger.error(e)

        # Step 2: Delete the CloudFormationStack if needed
        if self.resources_vpc_config is None and self.create_vpc_stack:
            vpc_stack = self.get_vpc_stack()
            try:
                vpc_stack.delete(aws_client)
            except Exception as e:
                logger.error("Stack deletion failed, please try again or delete manually")
                logger.error(e)

        # Step 3: Delete the EksCluster
        service_client = self.get_service_client(aws_client)
        self.active_resource = None
        try:
            delete_response = service_client.delete_cluster(name=self.name)
            logger.debug(f"EksCluster: {delete_response}")
            return True
        except Exception as e:
            logger.error(f"{self.get_resource_type()} could not be deleted.")
            logger.error("Please try again or delete resources manually.")
            logger.error(e)
        return False

    def post_delete(self, aws_client: AwsApiClient) -> bool:
        # Wait for Cluster to be deleted
        if self.wait_for_delete:
            try:
                print_info(f"Waiting for {self.get_resource_type()} to be deleted.")
                waiter = self.get_service_client(aws_client).get_waiter("cluster_deleted")
                waiter.wait(
                    name=self.name,
                    WaiterConfig={
                        "Delay": self.waiter_delay,
                        "MaxAttempts": self.waiter_max_attempts,
                    },
                )
            except Exception as e:
                logger.error("Waiter failed.")
                logger.error(e)

        # Update kubeconfig if needed
        if self.manage_kubeconfig:
            return self.clean_kubeconfig(aws_client=aws_client)
        return True

    def get_eks_iam_role(self) -> IamRole:
        if self.role is not None:
            return self.role

        policy_arns = ["arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"]
        if self.add_policy_arns is not None and isinstance(self.add_policy_arns, list):
            policy_arns.extend(self.add_policy_arns)

        return IamRole(
            name=self.role_name or f"{self.name}-role",
            assume_role_policy_document=dedent(
                """\
            {
              "Version": "2012-10-17",
              "Statement": [
                {
                  "Effect": "Allow",
                  "Principal": {
                    "Service": "eks.amazonaws.com"
                  },
                  "Action": "sts:AssumeRole"
                }
              ]
            }
            """
            ),
            policy_arns=policy_arns,
        )

    def get_vpc_stack(self) -> CloudFormationStack:
        if self.vpc_stack is not None:
            return self.vpc_stack
        return CloudFormationStack(
            name=self.vpc_stack_name or f"{self.name}-vpc",
            template_url=self.vpc_stack_template_url,
            skip_create=self.skip_create,
            skip_delete=self.skip_delete,
            wait_for_create=self.wait_for_create,
            wait_for_delete=self.wait_for_delete,
        )

    def get_subnets(self, aws_client: AwsApiClient, vpc_stack: Optional[CloudFormationStack] = None) -> List[str]:
        subnet_ids: List[str] = []

        # Option 1: Get subnets from the resources_vpc_config provided by the user
        if self.resources_vpc_config is not None and "subnetIds" in self.resources_vpc_config:
            subnet_ids = self.resources_vpc_config["subnetIds"]
            if not isinstance(subnet_ids, list):
                raise TypeError(f"resources_vpc_config.subnetIds must be a list of strings, not {type(subnet_ids)}")
            return subnet_ids

        # Option 2: Get subnets from the cloudformation VPC stack
        if vpc_stack is None:
            vpc_stack = self.get_vpc_stack()

        if self.use_public_subnets:
            public_subnets: Optional[List[str]] = vpc_stack.get_public_subnets(aws_client)
            if public_subnets is not None:
                subnet_ids.extend(public_subnets)

        if self.use_private_subnets:
            private_subnets: Optional[List[str]] = vpc_stack.get_private_subnets(aws_client)
            if private_subnets is not None:
                subnet_ids.extend(private_subnets)

        if self.subnet_az is not None:
            azs_filter = []
            if isinstance(self.subnet_az, str):
                azs_filter.append(self.subnet_az)
            elif isinstance(self.subnet_az, list):
                azs_filter.extend(self.subnet_az)

            subnet_ids = [
                subnet_id
                for subnet_id in subnet_ids
                if Subnet(name=subnet_id).get_availability_zone(aws_client=aws_client) in azs_filter
            ]
        return subnet_ids

    def get_eks_resources_vpc_config(
        self, aws_client: AwsApiClient, vpc_stack: CloudFormationStack
    ) -> Dict[str, List[Any]]:
        if self.resources_vpc_config is not None:
            return self.resources_vpc_config

        # Build resources_vpc_config using vpc_stack
        # get the VPC physical_resource_id
        # vpc_stack_resource = vpc_stack.get_stack_resource(aws_client, "VPC")
        # vpc_physical_resource_id = (
        #     vpc_stack_resource.physical_resource_id
        #     if vpc_stack_resource is not None
        #     else None
        # )
        # # logger.debug(f"vpc_physical_resource_id: {vpc_physical_resource_id}")

        # get the ControlPlaneSecurityGroup physical_resource_id
        sg_stack_resource = vpc_stack.get_stack_resource(aws_client, "ControlPlaneSecurityGroup")
        sg_physical_resource_id = sg_stack_resource.physical_resource_id if sg_stack_resource is not None else None
        security_group_ids = [sg_physical_resource_id] if sg_physical_resource_id is not None else []
        if self.add_security_groups is not None and isinstance(self.add_security_groups, list):
            security_group_ids.extend(self.add_security_groups)
        logger.debug(f"security_group_ids: {security_group_ids}")

        subnet_ids: List[str] = self.get_subnets(aws_client, vpc_stack)
        if self.add_subnets is not None and isinstance(self.add_subnets, list):
            subnet_ids.extend(self.add_subnets)
        logger.debug(f"subnet_ids: {subnet_ids}")

        resources_vpc_config: Dict[str, Any] = {
            "subnetIds": subnet_ids,
            "securityGroupIds": security_group_ids,
        }

        if self.endpoint_public_access is not None:
            resources_vpc_config["endpointPublicAccess"] = self.endpoint_public_access
        if self.endpoint_private_access is not None:
            resources_vpc_config["endpointPrivateAccess"] = self.endpoint_private_access
        if self.public_access_cidrs is not None:
            resources_vpc_config["publicAccessCidrs"] = self.public_access_cidrs

        return resources_vpc_config

    def get_subnets_in_order(self, aws_client: AwsApiClient) -> List[str]:
        """
        Returns the subnet_ids in the following order:
            - User provided subnets
            - Private subnets from the VPC stack
            - Public subnets from the VPC stack
        """
        # Option 1: Get subnets from the resources_vpc_config provided by the user
        if self.resources_vpc_config is not None and "subnetIds" in self.resources_vpc_config:
            subnet_ids = self.resources_vpc_config["subnetIds"]
            if not isinstance(subnet_ids, list):
                raise TypeError(f"resources_vpc_config.subnetIds must be a list of strings, not {type(subnet_ids)}")
            return subnet_ids

        # Option 2: Get private subnets from the VPC stack
        vpc_stack = self.get_vpc_stack()
        if self.use_private_subnets:
            private_subnets: Optional[List[str]] = vpc_stack.get_private_subnets(aws_client)
            if private_subnets is not None:
                return private_subnets

        # Option 3: Get public subnets from the VPC stack
        if self.use_public_subnets:
            public_subnets: Optional[List[str]] = vpc_stack.get_public_subnets(aws_client)
            if public_subnets is not None:
                return public_subnets
        return []

    def get_kubeconfig_cluster_name(self) -> str:
        return self.kubeconfig_cluster_name or self.name

    def get_kubeconfig_user_name(self) -> str:
        return self.kubeconfig_cluster_user or self.name

    def get_kubeconfig_context_name(self) -> str:
        return self.kubeconfig_cluster_context or self.name

    def write_kubeconfig(self, aws_client: AwsApiClient) -> bool:
        # Step 1: Get the EksCluster to generate the kubeconfig for
        eks_cluster = self._read(aws_client)
        if eks_cluster is None:
            logger.warning(f"EKSCluster not available: {self.name}")
            return False

        # Step 2: Get EksCluster cert, endpoint & arn
        try:
            cluster_cert = eks_cluster.get("cluster", {}).get("certificateAuthority", {}).get("data", None)
            logger.debug(f"cluster_cert: {cluster_cert}")

            cluster_endpoint = eks_cluster.get("cluster", {}).get("endpoint", None)
            logger.debug(f"cluster_endpoint: {cluster_endpoint}")

            cluster_arn = eks_cluster.get("cluster", {}).get("arn", None)
            logger.debug(f"cluster_arn: {cluster_arn}")
        except Exception as e:
            logger.error("Cannot read EKSCluster")
            logger.error(e)
            return False

        # from phi.k8s.enums.api_version import ApiVersion
        # from phi.k8s.resource.kubeconfig import (
        #     Kubeconfig,
        #     KubeconfigCluster,
        #     KubeconfigClusterConfig,
        #     KubeconfigContext,
        #     KubeconfigContextSpec,
        #     KubeconfigUser,
        # )
        #
        # # Step 3: Build Kubeconfig components
        # # 3.1 Build KubeconfigCluster config
        # new_cluster = KubeconfigCluster(
        #     name=self.get_kubeconfig_cluster_name(),
        #     cluster=KubeconfigClusterConfig(
        #         server=str(cluster_endpoint),
        #         certificate_authority_data=str(cluster_cert),
        #     ),
        # )
        #
        # # 3.2 Build KubeconfigUser config
        # new_user_exec_args = ["eks", "get-token", "--cluster-name", self.name]
        # if aws_client.aws_region is not None:
        #     new_user_exec_args.extend(["--region", aws_client.aws_region])
        # # Assume the role if the role_arn is provided
        # if self.kubeconfig_role_arn is not None:
        #     new_user_exec_args.extend(["--role-arn", self.kubeconfig_role_arn])
        # # Otherwise if role is provided, use that to get the role arn
        # elif self.kubeconfig_role is not None:
        #     _arn = self.kubeconfig_role.get_arn(aws_client=aws_client)
        #     if _arn is not None:
        #         new_user_exec_args.extend(["--role-arn", _arn])
        #
        # new_user_exec: Dict[str, Any] = {
        #     "apiVersion": ApiVersion.CLIENT_AUTHENTICATION_V1BETA1.value,
        #     "command": "aws",
        #     "args": new_user_exec_args,
        # }
        # if aws_client.aws_profile is not None:
        #     new_user_exec["env"] = [{"name": "AWS_PROFILE", "value": aws_client.aws_profile}]
        #
        # new_user = KubeconfigUser(
        #     name=self.get_kubeconfig_user_name(),
        #     user={"exec": new_user_exec},
        # )
        #
        # # 3.3 Build KubeconfigContext config
        # new_context = KubeconfigContext(
        #     name=self.get_kubeconfig_context_name(),
        #     context=KubeconfigContextSpec(
        #         cluster=new_cluster.name,
        #         user=new_user.name,
        #     ),
        # )
        # current_context = new_context.name
        # cluster_config: KubeconfigCluster
        #
        # # Step 4: Get existing Kubeconfig
        # kubeconfig_path = self.kubeconfig_path
        # if kubeconfig_path is None:
        #     logger.error(f"kubeconfig_path is None")
        #     return False
        #
        # kubeconfig: Optional[Any] = Kubeconfig.read_from_file(kubeconfig_path)
        #
        # # Step 5: Parse through the existing config to determine if
        # # an update is required. By the end of this logic
        # # if write_kubeconfig = False then no changes to kubeconfig are needed
        # # if write_kubeconfig = True then we should write the kubeconfig file
        # write_kubeconfig = False
        #
        # # Kubeconfig exists and is valid
        # if kubeconfig is not None and isinstance(kubeconfig, Kubeconfig):
        #     # Update Kubeconfig.clusters:
        #     # If a cluster with the same name exists in Kubeconfig.clusters
        #     #   - check if server and cert values match, if not, remove the existing cluster
        #     #   and add the new cluster config. Mark cluster_config_exists = True
        #     # If a cluster with the same name does not exist in Kubeconfig.clusters
        #     #   - add the new cluster config
        #     cluster_config_exists = False
        #     for idx, _cluster in enumerate(kubeconfig.clusters, start=0):
        #         if _cluster.name == new_cluster.name:
        #             cluster_config_exists = True
        #             if (
        #                 _cluster.cluster.server != new_cluster.cluster.server
        #                 or _cluster.cluster.certificate_authority_data
        #                 != new_cluster.cluster.certificate_authority_data
        #             ):
        #                 logger.debug("Kubeconfig.cluster mismatch, updating cluster config")
        #                 removed_cluster_config = kubeconfig.clusters.pop(idx)
        #                 # logger.debug(
        #                 #     f"removed_cluster_config: {removed_cluster_config}"
        #                 # )
        #                 kubeconfig.clusters.append(new_cluster)
        #                 write_kubeconfig = True
        #     if not cluster_config_exists:
        #         logger.debug("Adding Kubeconfig.cluster")
        #         kubeconfig.clusters.append(new_cluster)
        #         write_kubeconfig = True
        #
        #     # Update Kubeconfig.users:
        #     # If a user with the same name exists in Kubeconfig.users -
        #     #   check if user spec matches, if not, remove the existing user
        #     #   and add the new user config. Mark user_config_exists = True
        #     # If a user with the same name does not exist in Kubeconfig.users -
        #     #   add the new user config
        #     user_config_exists = False
        #     for idx, _user in enumerate(kubeconfig.users, start=0):
        #         if _user.name == new_user.name:
        #             user_config_exists = True
        #             if _user.user != new_user.user:
        #                 logger.debug("Kubeconfig.user mismatch, updating user config")
        #                 removed_user_config = kubeconfig.users.pop(idx)
        #                 # logger.debug(f"removed_user_config: {removed_user_config}")
        #                 kubeconfig.users.append(new_user)
        #                 write_kubeconfig = True
        #     if not user_config_exists:
        #         logger.debug("Adding Kubeconfig.user")
        #         kubeconfig.users.append(new_user)
        #         write_kubeconfig = True
        #
        #     # Update Kubeconfig.contexts:
        #     # If a context with the same name exists in Kubeconfig.contexts -
        #     #   check if context spec matches, if not, remove the existing context
        #     #   and add the new context. Mark context_config_exists = True
        #     # If a context with the same name does not exist in Kubeconfig.contexts -
        #     #   add the new context config
        #     context_config_exists = False
        #     for idx, _context in enumerate(kubeconfig.contexts, start=0):
        #         if _context.name == new_context.name:
        #             context_config_exists = True
        #             if _context.context != new_context.context:
        #                 logger.debug("Kubeconfig.context mismatch, updating context config")
        #                 removed_context_config = kubeconfig.contexts.pop(idx)
        #                 # logger.debug(
        #                 #     f"removed_context_config: {removed_context_config}"
        #                 # )
        #                 kubeconfig.contexts.append(new_context)
        #                 write_kubeconfig = True
        #     if not context_config_exists:
        #         logger.debug("Adding Kubeconfig.context")
        #         kubeconfig.contexts.append(new_context)
        #         write_kubeconfig = True
        #
        #     if kubeconfig.current_context is None or kubeconfig.current_context != current_context:
        #         logger.debug("Updating Kubeconfig.current_context")
        #         kubeconfig.current_context = current_context
        #         write_kubeconfig = True
        # else:
        #     # Kubeconfig does not exist or is not valid
        #     # Create a new Kubeconfig
        #     logger.info(f"Creating new Kubeconfig")
        #     kubeconfig = Kubeconfig(
        #         clusters=[new_cluster],
        #         users=[new_user],
        #         contexts=[new_context],
        #         current_context=current_context,
        #     )
        #     write_kubeconfig = True
        #
        # # if kubeconfig:
        # #     logger.debug("Kubeconfig:\n{}".format(kubeconfig.json(exclude_none=True, by_alias=True, indent=4)))
        #
        # # Step 5: Write Kubeconfig if an update is made
        # if write_kubeconfig:
        #     return kubeconfig.write_to_file(kubeconfig_path)
        # else:
        #     logger.info("Kubeconfig up-to-date")
        return True

    def clean_kubeconfig(self, aws_client: AwsApiClient) -> bool:
        logger.debug(f"TO_DO: Cleaning kubeconfig at {str(self.kubeconfig_path)}")
        return True

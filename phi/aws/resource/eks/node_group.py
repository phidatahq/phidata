from typing import Optional, Any, Dict, List, Union, cast
from typing_extensions import Literal
from textwrap import dedent

from phi.aws.api_client import AwsApiClient
from phi.aws.resource.base import AwsResource
from phi.aws.resource.ec2.subnet import Subnet
from phi.aws.resource.eks.cluster import EksCluster
from phi.aws.resource.iam.role import IamRole
from phi.cli.console import print_info
from phi.utils.log import logger


class EksNodeGroup(AwsResource):
    """
    An Amazon EKS managed node group is an Amazon EC2 Auto Scaling group and associated EC2
    instances that are managed by Amazon Web Services for an Amazon EKS cluster.

    An Auto Scaling group is a group of EC2 instances that are combined into one management unit.
    When you set up an auto-scaling group, you specify a scaling policy and AWS will apply that policy to make sure
    that a certain number of instances is automatically running in your group. If the number of instances drops below a
    certain value, or if the load increases (depending on the policy),
    then AWS will automatically spin up new instances for you.

    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/eks.html
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/eks.html#EKS.Client.create_nodegroup
    """

    resource_type: Optional[str] = "EksNodeGroup"
    service_name: str = "eks"

    # Name for the node group
    name: str
    # The cluster to create the EksNodeGroup in
    eks_cluster: EksCluster

    # The IAM role to associate with your node group.
    # The Amazon EKS worker node kubelet daemon makes calls to Amazon Web Services APIs on your behalf.
    # Nodes receive permissions for these API calls through an IAM instance profile and associated policies.
    # Before you can launch nodes and register them into a cluster,
    # you must create an IAM role for those nodes to use when they are launched.

    # ARN for the node group IAM role to use
    node_role_arn: Optional[str] = None
    # If node_role_arn is None, a default role is created if create_role is True
    create_role: bool = True
    # If node_role is None, a default node_role is created using node_role_name
    node_role: Optional[IamRole] = None
    # Name for the default node_role when role is None, use "name-iam-role" if not provided
    node_role_name: Optional[str] = None
    # Provide a list of policy ARNs to attach to the node group role
    add_policy_arns: Optional[List[str]] = None

    # The scaling configuration details for the Auto Scaling group
    # Users can provide a dict for scaling config or use min/max/desired values below
    scaling_config: Optional[Dict[str, Union[str, int]]] = None
    # The minimum number of nodes that the managed node group can scale in to.
    min_size: Optional[int] = None
    # The maximum number of nodes that the managed node group can scale out to.
    max_size: Optional[int] = None
    # The current number of nodes that the managed node group should maintain.
    # WARNING: If you use Cluster Autoscaler, you shouldn't change the desired_size value directly,
    # as this can cause the Cluster Autoscaler to suddenly scale up or scale down.
    # Whenever this parameter changes, the number of worker nodes in the node group is updated to
    # the specified size. If this parameter is given a value that is smaller than the current number of
    # running worker nodes, the necessary number of worker nodes are terminated to match the given value.
    desired_size: Optional[int] = None
    # The root device disk size (in GiB) for your node group instances.
    # The default disk size is 20 GiB. If you specify launchTemplate,
    # then don't specify diskSize, or the node group deployment will fail.
    disk_size: Optional[int] = None
    # The subnets to use for the Auto Scaling group that is created for your node group.
    # If you specify launchTemplate, then don't specify SubnetId in your launch template,
    # or the node group deployment will fail.
    # For more information about using launch templates with Amazon EKS,
    # see Launch template support in the Amazon EKS User Guide.
    subnets: Optional[List[str]] = None
    # Filter subnets using availability zones
    subnet_az: Optional[Union[str, List[str]]] = None
    # Specify the instance types for a node group.
    # If you specify a GPU instance type, be sure to specify AL2_x86_64_GPU with the amiType parameter.
    # If you specify launchTemplate , then you can specify zero or one instance type in your launch template
    # or you can specify 0-20 instance types for instanceTypes .
    # If however, you specify an instance type in your launch template and specify any instanceTypes ,
    # the node group deployment will fail. If you don't specify an instance type in a launch template
    # or for instance_types, then t3.medium is used, by default. If you specify Spot for capacityType,
    # then we recommend specifying multiple values for instanceTypes .
    instance_types: Optional[List[str]] = None
    # The AMI type for your node group. GPU instance types should use the AL2_x86_64_GPU AMI type.
    # Non-GPU instances should use the AL2_x86_64 AMI type.
    # Arm instances should use the AL2_ARM_64 AMI type.
    # All types use the Amazon EKS optimized Amazon Linux 2 AMI.
    # If you specify launchTemplate , and your launch template uses a custom AMI,
    # then don't specify amiType , or the node group deployment will fail.
    ami_type: Optional[
        Literal[
            "AL2_x86_64",
            "AL2_x86_64_GPU",
            "AL2_ARM_64",
            "CUSTOM",
            "BOTTLEROCKET_ARM_64",
            "BOTTLEROCKET_x86_64",
        ]
    ] = None
    # The remote access (SSH) configuration to use with your node group.
    # If you specify launchTemplate, then don't specify remoteAccess, or the node group deployment will fail. For
    # Keys:
    #   ec2SshKey (string) -- The Amazon EC2 SSH key that provides access for SSH communication with the nodes
    #   in the managed node group. For more information, see Amazon EC2 key pairs and Linux instances in the
    #   Amazon Elastic Compute Cloud User Guide for Linux Instances .
    #   sourceSecurityGroups (list) -- The security groups that are allowed SSH access (port 22) to the nodes.
    #   If you specify an Amazon EC2 SSH key but do not specify a source security group when you create
    #   a managed node group, then port 22 on the nodes is opened to the internet (0.0.0.0/0).
    #   For more information, see Security Groups for Your VPC in the Amazon Virtual Private Cloud User Guide .
    remote_access: Optional[Dict[str, str]] = None
    # The Kubernetes labels to be applied to the nodes in the node group when they are created.
    labels: Optional[Dict[str, str]] = None
    # The Kubernetes taints to be applied to the nodes in the node group.
    taints: Optional[List[dict]] = None
    # The metadata to apply to the node group to assist with categorization and organization.
    # Each tag consists of a key and an optional value. You define both.
    # Node group tags do not propagate to any other resources associated with the node group,
    # such as the Amazon EC2 instances or subnets.
    tags: Optional[Dict[str, str]] = None
    # Unique, case-sensitive identifier that you provide to ensure the idempotency of the request.
    # This field is autopopulated if not provided.
    client_request_token: Optional[str] = None
    # An object representing a node group's launch template specification.
    # If specified, then do not specify instanceTypes, diskSize, or remoteAccess and make sure that the launch template
    # meets the requirements in launchTemplateSpecification .
    launch_template: Optional[Dict[str, str]] = None
    # The node group update configuration.
    update_config: Optional[Dict[str, int]] = None
    # The capacity type for your node group.
    capacity_type: Optional[Literal["ON_DEMAND", "SPOT"]] = None
    # The Kubernetes version to use for your managed nodes.
    # By default, the Kubernetes version of the cluster is used, and this is the only accepted specified value.
    # If you specify launchTemplate , and your launch template uses a custom AMI,
    # then don't specify version , or the node group deployment will fail.
    version: Optional[str] = None
    # The AMI version of the Amazon EKS optimized AMI to use with your node group.
    # By default, the latest available AMI version for the node group's current Kubernetes version is used.
    release_version: Optional[str] = None

    # provided by api on create
    created_at: Optional[str] = None
    nodegroup_status: Optional[str] = None

    # provided by api on update
    update_id: Optional[str] = None
    update_status: Optional[str] = None

    # bump the wait time for Eks to 30 seconds
    waiter_delay: int = 30

    def _create(self, aws_client: AwsApiClient) -> bool:
        """Creates a NodeGroup for your Amazon EKS cluster.

        Args:
            aws_client: The AwsApiClient for the current cluster
        """
        print_info(f"Creating {self.get_resource_type()}: {self.get_resource_name()}")

        # Step 1: Get NodeGroup IamRole
        nodegroup_iam_role_arn = self.node_role_arn
        if nodegroup_iam_role_arn is None and self.create_role:
            # Create NodeGroup IamRole and get nodegroup_iam_role_arn
            nodegroup_iam_role = self.get_nodegroup_iam_role()
            try:
                nodegroup_iam_role.create(aws_client)
                nodegroup_iam_role_arn = nodegroup_iam_role.read(aws_client).arn
                print_info(f"ARN for {nodegroup_iam_role.name}: {nodegroup_iam_role_arn}")
            except Exception as e:
                logger.error("NodeGroup IamRole creation failed, please fix and try again")
                logger.error(e)
                return False
        if nodegroup_iam_role_arn is None:
            logger.error("IamRole ARN not available, please fix and try again")
            return False

        # Step 2: Get the subnets
        subnets: Optional[List[str]] = self.subnets
        if subnets is None:
            # Use subnets from EKSCluster if subnets not provided
            subnets = self.eks_cluster.get_subnets(aws_client=aws_client)
            # Filter subnets using availability zones
            if self.subnet_az is not None:
                azs_filter = []
                if isinstance(self.subnet_az, str):
                    azs_filter.append(self.subnet_az)
                elif isinstance(self.subnet_az, list):
                    azs_filter.extend(self.subnet_az)

                subnets = [
                    subnet_id
                    for subnet_id in subnets
                    if Subnet(name=subnet_id).get_availability_zone(aws_client=aws_client) in azs_filter
                ]
            logger.debug(f"Using subnets from EKSCluster: {subnets}")
        # cast for type checker
        subnets = cast(List[str], subnets)

        # Step 3: Get the scaling_config
        scaling_config: Optional[Dict[str, Union[str, int]]] = self.scaling_config
        if scaling_config is None:
            # Build the scaling_config
            if self.min_size is not None:
                if scaling_config is None:
                    scaling_config = {}
                scaling_config["minSize"] = self.min_size
                # use min_size as the default for maxSize/desiredSize incase maxSize/desiredSize is not provided
                scaling_config["maxSize"] = self.min_size
                scaling_config["desiredSize"] = self.min_size
            if self.max_size is not None:
                if scaling_config is None:
                    scaling_config = {}
                scaling_config["maxSize"] = self.max_size
            if self.desired_size is not None:
                if scaling_config is None:
                    scaling_config = {}
                scaling_config["desiredSize"] = self.desired_size

        # create a dict of args which are not null, otherwise aws type validation fails
        not_null_args: Dict[str, Any] = {}
        if scaling_config is not None:
            not_null_args["scalingConfig"] = scaling_config
        if self.disk_size is not None:
            not_null_args["diskSize"] = self.disk_size
        if self.instance_types is not None:
            not_null_args["instanceTypes"] = self.instance_types
        if self.ami_type is not None:
            not_null_args["amiType"] = self.ami_type
        if self.remote_access is not None:
            not_null_args["remoteAccess"] = self.remote_access
        if self.labels is not None:
            not_null_args["labels"] = self.labels
        if self.taints is not None:
            not_null_args["taints"] = self.taints
        if self.tags is not None:
            not_null_args["tags"] = self.tags
        if self.client_request_token is not None:
            not_null_args["clientRequestToken"] = self.client_request_token
        if self.launch_template is not None:
            not_null_args["launchTemplate"] = self.launch_template
        if self.update_config is not None:
            not_null_args["updateConfig"] = self.update_config
        if self.capacity_type is not None:
            not_null_args["capacityType"] = self.capacity_type
        if self.version is not None:
            not_null_args["version"] = self.version
        if self.release_version is not None:
            not_null_args["release_version"] = self.release_version

        # Step 4: Create EksNodeGroup
        service_client = self.get_service_client(aws_client)
        try:
            create_response = service_client.create_nodegroup(
                clusterName=self.eks_cluster.name,
                nodegroupName=self.name,
                subnets=subnets,
                nodeRole=nodegroup_iam_role_arn,
                **not_null_args,
            )
            logger.debug(f"EksNodeGroup: {create_response}")
            nodegroup_dict = create_response.get("nodegroup", {})

            # Validate EksNodeGroup creation
            self.created_at = nodegroup_dict.get("createdAt", None)
            self.nodegroup_status = nodegroup_dict.get("status", None)
            logger.debug(f"created_at: {self.created_at}")
            logger.debug(f"nodegroup_status: {self.nodegroup_status}")
            if self.created_at is not None:
                print_info(f"EksNodeGroup created: {self.name}")
                self.active_resource = create_response
                return True
        except service_client.exceptions.ResourceInUseException:
            print_info(f"EksNodeGroup already exists: {self.name}")
            return True
        except Exception as e:
            logger.error(f"{self.get_resource_type()} could not be created.")
            logger.error(e)
        return False

    def post_create(self, aws_client: AwsApiClient) -> bool:
        # Wait for EksNodeGroup to be created
        if self.wait_for_create:
            try:
                print_info(f"Waiting for {self.get_resource_type()} to be created.")
                waiter = self.get_service_client(aws_client).get_waiter("nodegroup_active")
                waiter.wait(
                    clusterName=self.eks_cluster.name,
                    nodegroupName=self.name,
                    WaiterConfig={
                        "Delay": self.waiter_delay,
                        "MaxAttempts": self.waiter_max_attempts,
                    },
                )
            except Exception as e:
                logger.error("Waiter failed.")
                logger.error(e)
        return True

    def _read(self, aws_client: AwsApiClient) -> Optional[Any]:
        """Returns the EksNodeGroup

        Args:
            aws_client: The AwsApiClient for the current cluster
        """
        logger.debug(f"Reading {self.get_resource_type()}: {self.get_resource_name()}")

        from botocore.exceptions import ClientError

        service_client = self.get_service_client(aws_client)
        try:
            describe_response = service_client.describe_nodegroup(
                clusterName=self.eks_cluster.name,
                nodegroupName=self.name,
            )
            # logger.debug(f"describe_response: {describe_response}")
            nodegroup_dict = describe_response.get("nodegroup", {})

            self.created_at = nodegroup_dict.get("createdAt", None)
            self.nodegroup_status = nodegroup_dict.get("status", None)
            logger.debug(f"NodeGroup created_at: {self.created_at}")
            logger.debug(f"NodeGroup status: {self.nodegroup_status}")
            if self.created_at is not None:
                logger.debug(f"EksNodeGroup found: {self.name}")
                self.active_resource = describe_response
        except ClientError as ce:
            logger.debug(f"ClientError: {ce}")
        except Exception as e:
            logger.error(f"Error reading {self.get_resource_type()}.")
            logger.error(e)
        return self.active_resource

    def _delete(self, aws_client: AwsApiClient) -> bool:
        """Deletes the EksNodeGroup

        Args:
            aws_client: The AwsApiClient for the current cluster
        """
        print_info(f"Deleting {self.get_resource_type()}: {self.get_resource_name()}")

        # Step 1: Delete the IamRole
        if self.node_role_arn is None and self.create_role:
            nodegroup_iam_role = self.get_nodegroup_iam_role()
            try:
                nodegroup_iam_role.delete(aws_client)
            except Exception as e:
                logger.error("IamRole deletion failed, please try again or delete manually")
                logger.error(e)

        # Step 2: Delete the NodeGroup
        service_client = self.get_service_client(aws_client)
        self.active_resource = None
        try:
            delete_response = service_client.delete_nodegroup(
                clusterName=self.eks_cluster.name,
                nodegroupName=self.name,
            )
            logger.debug(f"EksNodeGroup: {delete_response}")
            return True
        except Exception as e:
            logger.error(f"{self.get_resource_type()} could not be deleted.")
            logger.error("Please try again or delete resources manually.")
            logger.error(e)
        return False

    def post_delete(self, aws_client: AwsApiClient) -> bool:
        # Wait for EksNodeGroup to be deleted
        if self.wait_for_delete:
            try:
                print_info(f"Waiting for {self.get_resource_type()} to be deleted.")
                waiter = self.get_service_client(aws_client).get_waiter("nodegroup_deleted")
                waiter.wait(
                    clusterName=self.eks_cluster.name,
                    nodegroupName=self.name,
                    WaiterConfig={
                        "Delay": self.waiter_delay,
                        "MaxAttempts": self.waiter_max_attempts,
                    },
                )
                return True
            except Exception as e:
                logger.error("Waiter failed.")
                logger.error(e)
        return True

    def get_nodegroup_iam_role(self) -> IamRole:
        """
        Create an IAM role and attach the required Amazon EKS IAM managed policy to it.
        """
        if self.node_role is not None:
            return self.node_role

        policy_arns = [
            "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
            "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
            "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
            "arn:aws:iam::aws:policy/AmazonS3FullAccess",
            "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy",
            "arn:aws:iam::aws:policy/service-role/AmazonEFSCSIDriverPolicy",
        ]
        if self.add_policy_arns is not None and isinstance(self.add_policy_arns, list):
            policy_arns.extend(self.add_policy_arns)

        return IamRole(
            name=self.node_role_name or f"{self.name}-iam-role",
            assume_role_policy_document=dedent(
                """\
            {
              "Version": "2012-10-17",
              "Statement": [
                {
                  "Effect": "Allow",
                  "Principal": {
                    "Service": "ec2.amazonaws.com"
                  },
                  "Action": "sts:AssumeRole"
                }
              ]
            }
            """
            ),
            policy_arns=policy_arns,
        )

    def _update(self, aws_client: AwsApiClient) -> bool:
        """Update EKsNodeGroup"""
        print_info(f"Updating {self.get_resource_type()}: {self.get_resource_name()}")

        scaling_config: Optional[Dict[str, Union[str, int]]] = self.scaling_config
        if scaling_config is None:
            # Build the scaling_config
            if self.min_size is not None:
                if scaling_config is None:
                    scaling_config = {}
                scaling_config["minSize"] = self.min_size
                # use min_size as the default for maxSize/desiredSize incase maxSize/desiredSize is not provided
                scaling_config["maxSize"] = self.min_size
                scaling_config["desiredSize"] = self.min_size
            if self.max_size is not None:
                if scaling_config is None:
                    scaling_config = {}
                scaling_config["maxSize"] = self.max_size
            if self.desired_size is not None:
                if scaling_config is None:
                    scaling_config = {}
                scaling_config["desiredSize"] = self.desired_size

        # TODO: Add logic to calculate updated_labels and updated_taints

        updated_labels = None
        updated_taints = None

        # create a dict of args which are not null, otherwise aws type validation fails
        not_null_args: Dict[str, Any] = {}
        if scaling_config is not None:
            not_null_args["scalingConfig"] = scaling_config
        if updated_labels is not None:
            not_null_args["labels"] = updated_labels
        if updated_taints is not None:
            not_null_args["taints"] = updated_taints
        if self.update_config is not None:
            not_null_args["updateConfig"] = self.update_config

        # Step 4: Update EksNodeGroup
        service_client = self.get_service_client(aws_client)
        try:
            update_response = service_client.update_nodegroup_config(
                clusterName=self.eks_cluster.name,
                nodegroupName=self.name,
                **not_null_args,
            )
            logger.debug(f"EksNodeGroup: {update_response}")
            nodegroup_dict = update_response.get("update", {})

            # Validate EksNodeGroup update
            self.update_id = nodegroup_dict.get("id", None)
            self.update_status = nodegroup_dict.get("status", None)
            logger.debug(f"update_id: {self.update_id}")
            logger.debug(f"update_status: {self.update_status}")
            if self.update_id is not None:
                print_info(f"EksNodeGroup updated: {self.name}")
                return True
        except Exception as e:
            logger.error(f"{self.get_resource_type()} could not be updated.")
            logger.error(e)
        return False

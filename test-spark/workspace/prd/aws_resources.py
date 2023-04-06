from phidata.aws.resource.group import (
    AcmCertificate,
    EksCluster,
    EksKubeconfig,
    EksNodeGroup,
    AwsResourceGroup,
    S3Bucket,
)

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
prd_logs_s3_bucket = S3Bucket(
    name=f"{ws_settings.prd_key}-logs",
    acl="private",
    skip_create=skip_create,
    skip_delete=skip_delete,
    wait_for_creation=wait_for_create,
    wait_for_deletion=wait_for_delete,
)
# S3 bucket for storing data
prd_data_s3_bucket = S3Bucket(
    name=f"{ws_settings.prd_key}-data",
    acl="private",
    skip_create=skip_create,
    skip_delete=skip_delete,
    wait_for_creation=wait_for_create,
    wait_for_deletion=wait_for_delete,
)

# -*- EKS settings
# Node Group label for Services
services_ng_label = {"app_type": "service"}
# Node Group label for Workers
workers_ng_label = {"app_type": "worker"}
# How to distribute pods across EKS nodes
# "kubernetes.io/hostname" means spread across nodes
topology_spread_key = "kubernetes.io/hostname"
topology_spread_max_skew = 2
topology_spread_when_unsatisfiable = "DoNotSchedule"

# -*- EKS cluster
prd_eks_cluster = EksCluster(
    name=f"{ws_settings.prd_key}-cluster",
    # To use custom subnets and security groups:
    #   Uncomment the resources_vpc_config and add subnets and security groups
    # resources_vpc_config={
    #     "subnetIds": ws_settings.subnet_ids,
    #     # "securityGroupIds": ws_settings.security_groups,
    # },
    tags=ws_settings.prd_tags,
    # Manage kubeconfig separately using an EksKubeconfig resource
    manage_kubeconfig=False,
    skip_create=skip_create,
    skip_delete=skip_delete,
    wait_for_creation=wait_for_create,
    wait_for_deletion=wait_for_delete,
)

# -*- EKS Kubeconfig
prd_eks_kubeconfig = EksKubeconfig(eks_cluster=prd_eks_cluster)

# -*- EKS cluster nodegroup for running core services
prd_services_eks_nodegroup = EksNodeGroup(
    name=f"{ws_settings.prd_key}-services-ng",
    min_size=2,
    max_size=5,
    desired_size=2,
    disk_size=64,
    instance_types=["m5.large"],
    eks_cluster=prd_eks_cluster,
    # Add the services label to the nodegroup
    labels=services_ng_label,
    tags=ws_settings.prd_tags,
    skip_create=skip_create,
    skip_delete=skip_delete,
    wait_for_creation=wait_for_create,
    wait_for_deletion=wait_for_delete,
)

# -*- EKS cluster nodegroup for running worker services
prd_worker_eks_nodegroup = EksNodeGroup(
    name=f"{ws_settings.prd_key}-workers-ng",
    min_size=2,
    max_size=5,
    desired_size=2,
    disk_size=64,
    instance_types=["m5.large"],
    eks_cluster=prd_eks_cluster,
    # Add the workers label to the nodegroup
    labels=workers_ng_label,
    tags=ws_settings.prd_tags,
    skip_create=skip_create,
    skip_delete=skip_delete,
    wait_for_creation=wait_for_create,
    wait_for_deletion=wait_for_delete,
)

# -*- ACM certificate for domain
prd_acm_certificate = AcmCertificate(
    name=f"{ws_settings.prd_key}-cert",
    domain_name=ws_settings.prd_domain,
    subject_alternative_names=[f"*.{ws_settings.prd_domain}"],
    # Store the certificate ARN in the certificate_summary_file
    store_cert_summary=True,
    certificate_summary_file=ws_settings.ws_dir.joinpath(
        "workspace", "aws", "acm", ws_settings.prd_domain
    ),
    skip_create=skip_create,
    skip_delete=skip_delete,
    wait_for_creation=wait_for_create,
    wait_for_deletion=wait_for_delete,
)

prd_aws_resources = AwsResourceGroup(
    name=ws_settings.prd_key,
    s3_buckets=[prd_logs_s3_bucket, prd_data_s3_bucket],
    eks_cluster=prd_eks_cluster,
    eks_kubeconfig=prd_eks_kubeconfig,
    eks_nodegroups=[prd_services_eks_nodegroup, prd_worker_eks_nodegroup],
    # Uncomment to create ACM certificate
    # acm_certificates=[prd_acm_certificate],
)

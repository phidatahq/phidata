from collections import OrderedDict
from typing import Dict, List, Type, Union

from phidata.aws.resource.base import AwsResource
from phidata.aws.resource.acm.certificate import AcmCertificate
from phidata.aws.resource.cloudformation.stack import CloudFormationStack
from phidata.aws.resource.ec2.volume import EbsVolume
from phidata.aws.resource.ecs.cluster import EcsCluster
from phidata.aws.resource.ecs.task_definition import EcsTaskDefinition
from phidata.aws.resource.eks.cluster import EksCluster
from phidata.aws.resource.ecs.service import EcsService
from phidata.aws.resource.eks.fargate_profile import EksFargateProfile
from phidata.aws.resource.eks.node_group import EksNodeGroup
from phidata.aws.resource.eks.kubeconfig import EksKubeconfig
from phidata.aws.resource.iam.role import IamRole
from phidata.aws.resource.iam.policy import IamPolicy
from phidata.aws.resource.glue.crawler import GlueCrawler
from phidata.aws.resource.s3.bucket import S3Bucket
from phidata.aws.resource.emr.cluster import EmrCluster
from phidata.aws.resource.rds.db_cluster import DbCluster
from phidata.aws.resource.rds.db_instance import DbInstance
from phidata.aws.resource.rds.db_subnet_group import DbSubnetGroup
from phidata.aws.resource.elasticache.cluster import CacheCluster
from phidata.aws.resource.elasticache.subnet_group import CacheSubnetGroup

# Use this as a type for an object which can hold any Aws Resource
AwsResourceType = Union[
    AcmCertificate,
    CloudFormationStack,
    EbsVolume,
    EksCluster,
    EksFargateProfile,
    EksNodeGroup,
    EksKubeconfig,
    IamRole,
    IamPolicy,
    GlueCrawler,
    S3Bucket,
    DbSubnetGroup,
    DbCluster,
    DbInstance,
    CacheSubnetGroup,
    CacheCluster,
    EmrCluster,
    EcsCluster,
    EcsTaskDefinition,
    EcsService,
]

# Use this as an ordered list to iterate over all Aws Resource Classes
# This list is the order in which resources should be installed as well.
AwsResourceTypeList: List[Type[AwsResource]] = [
    IamRole,
    IamPolicy,
    S3Bucket,
    EbsVolume,
    AcmCertificate,
    CloudFormationStack,
    GlueCrawler,
    DbSubnetGroup,
    DbCluster,
    DbInstance,
    CacheSubnetGroup,
    CacheCluster,
    EcsCluster,
    EcsTaskDefinition,
    EcsService,
    EksCluster,
    EksKubeconfig,
    EksFargateProfile,
    EksNodeGroup,
    EmrCluster,
]

# Map Aws resource alias' to their type
_aws_resource_type_names: Dict[str, Type[AwsResource]] = {
    aws_type.__name__.lower(): aws_type for aws_type in AwsResourceTypeList
}
_aws_resource_type_aliases: Dict[str, Type[AwsResource]] = {
    "s3": S3Bucket,
    "volume": EbsVolume,
}

AwsResourceAliasToTypeMap: Dict[str, Type[AwsResource]] = dict(
    **_aws_resource_type_names, **_aws_resource_type_aliases
)

# Maps each AwsResource to an install weight
# lower weight AwsResource(s) get installed first
AwsResourceInstallOrder: Dict[str, int] = OrderedDict(
    {
        resource_type.__name__: idx
        for idx, resource_type in enumerate(AwsResourceTypeList, start=1)
    }
)

from typing import List, Optional

from pydantic import BaseModel

from phidata.aws.resource.acm.certificate import AcmCertificate
from phidata.aws.resource.cloudformation.stack import CloudFormationStack
from phidata.aws.resource.ec2.volume import EbsVolume
from phidata.aws.resource.ecs.cluster import EcsCluster
from phidata.aws.resource.ecs.container import EcsContainer
from phidata.aws.resource.ecs.task_definition import EcsTaskDefinition
from phidata.aws.resource.ecs.volume import EcsVolume
from phidata.aws.resource.ecs.service import EcsService
from phidata.aws.resource.eks.cluster import EksCluster
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


class AwsResourceGroup(BaseModel):
    """The AwsResourceGroup class contains the data for all AwsResources"""

    name: str = "default"
    enabled: bool = True
    weight: int = 100

    iam_roles: Optional[List[IamRole]] = None
    iam_policies: Optional[List[IamPolicy]] = None
    acm_certificates: Optional[List[AcmCertificate]] = None
    s3_buckets: Optional[List[S3Bucket]] = None
    cache_clusters: Optional[List[CacheCluster]] = None
    cache_subnet_groups: Optional[List[CacheSubnetGroup]] = None
    db_clusters: Optional[List[DbCluster]] = None
    db_subnet_groups: Optional[List[DbSubnetGroup]] = None
    db_instances: Optional[List[DbInstance]] = None
    ecs_clusters: Optional[List[EcsCluster]] = None
    ecs_task_definitions: Optional[List[EcsTaskDefinition]] = None
    ecs_services: Optional[List[EcsService]] = None
    volumes: Optional[List[EbsVolume]] = None
    cloudformation_stacks: Optional[List[CloudFormationStack]] = None
    eks_cluster: Optional[EksCluster] = None
    eks_kubeconfig: Optional[EksKubeconfig] = None
    eks_fargate_profiles: Optional[List[EksFargateProfile]] = None
    eks_nodegroups: Optional[List[EksNodeGroup]] = None
    crawlers: Optional[List[GlueCrawler]] = None
    emr: Optional[List[EmrCluster]] = None

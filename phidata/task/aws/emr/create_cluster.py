from typing import Optional

from phidata.utils.log import logger
from phidata.infra.aws.resource.emr.cluster import EmrCluster
from phidata.task import PythonTask, PythonTaskArgs


class CreateEmrClusterArgs(PythonTaskArgs):
    cluster: EmrCluster


class CreateEmrCluster(PythonTask):
    def __init__(
        self,
        cluster: EmrCluster,
        name: str = "create_emr_cluster",
        task_id: Optional[str] = None,
        dag_id: Optional[str] = None,
        version: Optional[str] = None,
        enabled: bool = True,
    ):
        super().__init__()
        try:
            self.args: CreateEmrClusterArgs = CreateEmrClusterArgs(
                cluster=cluster,
                name=name,
                task_id=task_id,
                dag_id=dag_id,
                version=version,
                enabled=enabled,
                entrypoint=create_emr_cluster,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    @property
    def cluster(self) -> EmrCluster:
        return self.args.cluster

    @cluster.setter
    def cluster(self, cluster: EmrCluster) -> None:
        if cluster is not None:
            self.args.cluster = cluster


def create_emr_cluster(**kwargs) -> bool:

    args: CreateEmrClusterArgs = CreateEmrClusterArgs(**kwargs)
    # logger.debug("CreateEmrClusterArgs: {}".format(args))

    create_success = args.cluster.create()
    if create_success:
        logger.info("Create EmrCluster: success")
    else:
        logger.error("Create EmrCluster: failed")
    return create_success

from typing import Optional

from phidata.utils.log import logger
from phidata.infra.aws.resource.emr.cluster import EmrCluster
from phidata.task import PythonTask, PythonTaskArgs


class DeleteEmrClusterArgs(PythonTaskArgs):
    cluster: EmrCluster


class DeleteEmrCluster(PythonTask):
    def __init__(
        self,
        cluster: EmrCluster,
        name: str = "delete_emr_cluster",
        task_id: Optional[str] = None,
        dag_id: Optional[str] = None,
        version: Optional[str] = None,
        enabled: bool = True,
    ):
        super().__init__()
        try:
            self.args: DeleteEmrClusterArgs = DeleteEmrClusterArgs(
                cluster=cluster,
                name=name,
                task_id=task_id,
                dag_id=dag_id,
                version=version,
                enabled=enabled,
                entrypoint=delete_emr_cluster,
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


def delete_emr_cluster(**kwargs) -> bool:

    args: DeleteEmrClusterArgs = DeleteEmrClusterArgs(**kwargs)
    # logger.debug("DeleteEmrClusterArgs: {}".format(args))

    delete_success = args.cluster.delete()
    if delete_success:
        logger.info("Delete EmrCluster: success")
    else:
        logger.error("Delete EmrCluster: failed")
    return delete_success

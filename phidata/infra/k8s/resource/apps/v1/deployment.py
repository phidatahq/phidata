from typing import List, Optional

from kubernetes.client import AppsV1Api
from kubernetes.client.models.v1_deployment import V1Deployment
from kubernetes.client.models.v1_deployment_list import V1DeploymentList
from kubernetes.client.models.v1_deployment_spec import V1DeploymentSpec
from kubernetes.client.models.v1_status import V1Status
from pydantic import Field

from phidata.infra.k8s.api_client import K8sApiClient
from phidata.infra.k8s.resource.base import K8sResource, K8sObject
from phidata.infra.k8s.resource.apps.v1.deployment_strategy import DeploymentStrategy
from phidata.infra.k8s.resource.core.v1.pod_template_spec import PodTemplateSpec
from phidata.infra.k8s.resource.meta.v1.label_selector import LabelSelector
from phidata.utils.dttm import utc_now_str
from phidata.utils.log import logger


class DeploymentSpec(K8sObject):
    """
    # https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#deploymentspec-v1-apps
    """

    resource_type: str = "DeploymentSpec"

    # Minimum number of seconds for which a newly created pod should be ready
    # without any of its container crashing, for it to be considered available.
    # Defaults to 0 (pod will be considered available as soon as it is ready)
    min_ready_seconds: Optional[int] = Field(None, alias="minReadySeconds")
    # Indicates that the deployment is paused.
    paused: Optional[bool] = None
    # The maximum time in seconds for a deployment to make progress before it is considered to be failed.
    # The deployment controller will continue to process failed deployments and a condition with a
    # ProgressDeadlineExceeded reason will be surfaced in the deployment status.
    # Note that progress will not be estimated during the time a deployment is paused.
    # Defaults to 600s.
    progress_deadline_seconds: Optional[int] = Field(
        None, alias="progressDeadlineSeconds"
    )
    replicas: Optional[int] = None
    # The number of old ReplicaSets to retain to allow rollback.
    # This is a pointer to distinguish between explicit zero and not specified.
    # Defaults to 10.
    revision_history_limit: Optional[int] = Field(None, alias="revisionHistoryLimit")
    # The selector field defines how the Deployment finds which Pods to manage
    selector: LabelSelector
    strategy: Optional[DeploymentStrategy] = None
    template: PodTemplateSpec

    def get_k8s_object(self) -> V1DeploymentSpec:

        # Return a V1DeploymentSpec object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_deployment_spec.py
        _strategy = self.strategy.get_k8s_object() if self.strategy else None
        _v1_deployment_spec = V1DeploymentSpec(
            min_ready_seconds=self.min_ready_seconds,
            paused=self.paused,
            progress_deadline_seconds=self.progress_deadline_seconds,
            replicas=self.replicas,
            revision_history_limit=self.revision_history_limit,
            selector=self.selector.get_k8s_object(),
            strategy=_strategy,
            template=self.template.get_k8s_object(),
        )
        return _v1_deployment_spec


class Deployment(K8sResource):
    """
    Deployments are used to run containers.
    Containers are run in Pods or ReplicaSets, and Deployments manages those Pods or ReplicaSets.
    A Deployment provides declarative updates for Pods and ReplicaSets.

    References:
        * Docs:
            https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#deployment-v1-apps
            https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
        * Type: https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_deployment.py
    """

    resource_type: str = "Deployment"

    spec: DeploymentSpec
    # If True, adds `kubectl.kubernetes.io/restartedAt` annotation on update
    # so the deployment is restarted even without any data change
    restart_on_update: bool = True

    # List of attributes to include in the K8s manifest
    fields_for_k8s_manifest: List[str] = ["spec"]

    def get_k8s_object(self) -> V1Deployment:
        """Creates a body for this Deployment"""

        # Return a V1Deployment object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_deployment.py
        _v1_deployment = V1Deployment(
            api_version=self.api_version,
            kind=self.kind,
            metadata=self.metadata.get_k8s_object(),
            spec=self.spec.get_k8s_object(),
        )
        return _v1_deployment

    @staticmethod
    def get_from_cluster(
        k8s_client: K8sApiClient, namespace: Optional[str] = None, **kwargs
    ) -> Optional[List[V1Deployment]]:
        """Reads Deployments from K8s cluster.

        Args:
            k8s_client: The K8sApiClient for the current Cluster
            namespace: Namespace to use.
        """
        apps_v1_api: AppsV1Api = k8s_client.apps_v1_api
        deploy_list: Optional[V1DeploymentList] = None
        if namespace:
            # logger.debug(f"Getting deploys for ns: {namespace}")
            deploy_list = apps_v1_api.list_namespaced_deployment(
                namespace=namespace, **kwargs
            )
        else:
            # logger.debug("Getting deploys for all namespaces")
            deploy_list = apps_v1_api.list_deployment_for_all_namespaces(**kwargs)

        deploys: Optional[List[V1Deployment]] = None
        if deploy_list:
            deploys = deploy_list.items
        # logger.debug(f"deploys: {deploys}")
        # logger.debug(f"deploys type: {type(deploys)}")
        return deploys

    def _create(self, k8s_client: K8sApiClient) -> bool:

        apps_v1_api: AppsV1Api = k8s_client.apps_v1_api
        k8s_object: V1Deployment = self.get_k8s_object()
        namespace = self.get_namespace()

        logger.debug("Creating: {}".format(self.get_resource_name()))
        v1_deployment: V1Deployment = apps_v1_api.create_namespaced_deployment(
            namespace=namespace,
            body=k8s_object,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("Created: {}".format(v1_deployment))
        if v1_deployment.metadata.creation_timestamp is not None:
            logger.debug("Deployment Created")
            self.active_resource = v1_deployment
            self.active_resource_class = V1Deployment
            return True
        logger.error("Deployment could not be created")
        return False

    def _read(self, k8s_client: K8sApiClient) -> Optional[V1Deployment]:
        """Returns the "Active" Deployment from the cluster"""

        namespace = self.get_namespace()
        active_resource: Optional[V1Deployment] = None
        active_resources: Optional[List[V1Deployment]] = self.get_from_cluster(
            k8s_client=k8s_client,
            namespace=namespace,
        )
        # logger.debug(f"Active Resources: {active_resources}")
        if active_resources is None:
            return None

        active_resources_dict = {
            _deploy.metadata.name: _deploy for _deploy in active_resources
        }

        deploy_name = self.get_resource_name()
        if deploy_name in active_resources_dict:
            active_resource = active_resources_dict[deploy_name]
            self.active_resource = active_resource
            logger.debug(f"Found active {deploy_name}")
        return active_resource

    def _update(self, k8s_client: K8sApiClient) -> bool:

        # update `spec.template.metadata` section
        # to add `kubectl.kubernetes.io/restartedAt` annotation
        # https://github.com/kubernetes-client/python/issues/1378#issuecomment-779323573
        if self.restart_on_update:
            if self.spec.template.metadata.annotations is None:
                self.spec.template.metadata.annotations = {}
            self.spec.template.metadata.annotations[
                "kubectl.kubernetes.io/restartedAt"
            ] = utc_now_str()
            logger.debug(f"annotations: {self.spec.template.metadata.annotations}")

        apps_v1_api: AppsV1Api = k8s_client.apps_v1_api
        deploy_name = self.get_resource_name()
        k8s_object: V1Deployment = self.get_k8s_object()
        namespace = self.get_namespace()

        logger.debug("Updating: {}".format(deploy_name))
        v1_deployment: V1Deployment = apps_v1_api.patch_namespaced_deployment(
            name=deploy_name,
            namespace=namespace,
            body=k8s_object,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        # logger.debug("Updated: {}".format(v1_deployment))
        if v1_deployment.metadata.creation_timestamp is not None:
            logger.debug("Deployment Updated")
            self.active_resource = v1_deployment
            self.active_resource_class = V1Deployment
            return True
        logger.error("Deployment could not be updated")
        return False

    def _delete(self, k8s_client: K8sApiClient) -> bool:

        apps_v1_api: AppsV1Api = k8s_client.apps_v1_api
        deploy_name = self.get_resource_name()
        namespace = self.get_namespace()

        logger.debug("Deleting: {}".format(deploy_name))
        self.active_resource = None
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_status.py
        delete_status: V1Status = apps_v1_api.delete_namespaced_deployment(
            name=deploy_name,
            namespace=namespace,
            async_req=self.async_req,
            pretty=self.pretty,
        )
        logger.debug("delete_status: {}".format(delete_status.status))
        if delete_status.status == "Success":
            logger.debug("Deployment Deleted")
            return True
        logger.error("Deployment could not be deleted")
        return False

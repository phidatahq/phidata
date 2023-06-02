from typing import Optional, Dict, Any, Union, List

from phidata.app.base_app import BaseApp, BaseAppArgs
from phidata.types.context import ContainerPathContext
from phidata.workspace.volume import WorkspaceVolumeType
from phidata.utils.log import logger


class K8sAppArgs(BaseAppArgs):
    # -*- Container Volumes
    # To mount the workspace directory on the container
    # Load the workspace from git using a git-sync sidecar
    create_git_sync_sidecar: bool = False
    # Required to create an initial copy of the workspace
    create_git_sync_init_container: bool = True
    git_sync_image_name: str = "k8s.gcr.io/git-sync"
    git_sync_image_tag: str = "v3.1.1"
    git_sync_repo: Optional[str] = None
    git_sync_branch: Optional[str] = None
    git_sync_wait: int = 1

    # -*- Container Configuration
    container_name: Optional[str] = None

    # -*- Pod Configuration
    pod_name: Optional[str] = None
    pod_annotations: Optional[Dict[str, str]] = None
    pod_node_selector: Optional[Dict[str, str]] = None

    # -*- Secret Configuration
    secret_name: Optional[str] = None

    # -*- Configmap Configuration
    configmap_name: Optional[str] = None

    # -*- Deployment Configuration
    replicas: int = 1
    deploy_name: Optional[str] = None
    # Type: ImagePullPolicy
    image_pull_policy: Optional[Any] = None
    # Type: RestartPolicy
    deploy_restart_policy: Optional[Any] = None
    deploy_labels: Optional[Dict[str, Any]] = None
    termination_grace_period_seconds: Optional[int] = None
    # Key to spread the pods across a topology
    topology_spread_key: Optional[str] = None
    # The degree to which pods may be unevenly distributed
    topology_spread_max_skew: Optional[int] = None
    # How to deal with a pod if it doesn't satisfy the spread constraint.
    topology_spread_when_unsatisfiable: Optional[str] = None

    # -*- Service Configuration
    create_service: bool = False
    service_name: Optional[str] = None
    # Type: ServiceType
    service_type: Optional[Any] = None
    # The port exposed by the service.
    service_port: int = 8000
    # The node_port exposed by the service if service_type = ServiceType.NODE_PORT
    service_node_port: Optional[int] = None
    # The target_port is the port to access on the pods targeted by the service.
    # It can be the port number or port name on the pod.
    service_target_port: Optional[Union[str, int]] = None
    # Extra ports exposed by the webserver service. Type: List[CreatePort]
    service_ports: Optional[List[Any]] = None
    service_labels: Optional[Dict[str, Any]] = None
    service_annotations: Optional[Dict[str, str]] = None
    # If ServiceType == ServiceType.LoadBalancer
    service_health_check_node_port: Optional[int] = None
    service_internal_traffic_policy: Optional[str] = None
    service_load_balancer_class: Optional[str] = None
    service_load_balancer_ip: Optional[str] = None
    service_load_balancer_source_ranges: Optional[List[str]] = None
    service_allocate_load_balancer_node_ports: Optional[bool] = None

    # -*- Ingress Configuration
    create_ingress: bool = False
    ingress_name: Optional[str] = None
    ingress_annotations: Optional[Dict[str, str]] = None

    # -*- RBAC Configuration
    use_rbac: bool = False
    # Create a Namespace with name ns_name & default values
    ns_name: Optional[str] = None
    # or Provide the full Namespace definition
    # Type: CreateNamespace
    namespace: Optional[Any] = None
    # Create a ServiceAccount with name sa_name & default values
    sa_name: Optional[str] = None
    # or Provide the full ServiceAccount definition
    # Type: CreateServiceAccount
    service_account: Optional[Any] = None
    # Create a ClusterRole with name cr_name & default values
    cr_name: Optional[str] = None
    # or Provide the full ClusterRole definition
    # Type: CreateClusterRole
    cluster_role: Optional[Any] = None
    # Create a ClusterRoleBinding with name crb_name & default values
    crb_name: Optional[str] = None
    # or Provide the full ClusterRoleBinding definition
    # Type: CreateClusterRoleBinding
    cluster_role_binding: Optional[Any] = None

    # Add additional Kubernetes resources to the App
    # Type: CreateSecret
    extra_secrets: Optional[List[Any]] = None
    # Type: CreateConfigMap
    extra_configmaps: Optional[List[Any]] = None
    # Type: CreateService
    extra_services: Optional[List[Any]] = None
    # Type: CreateDeployment
    extra_deployments: Optional[List[Any]] = None
    # Type: CreatePersistentVolume
    extra_pvs: Optional[List[Any]] = None
    # Type: CreatePVC
    extra_pvcs: Optional[List[Any]] = None
    # Type: CreateContainer
    extra_containers: Optional[List[Any]] = None
    # Type: CreateContainer
    extra_init_containers: Optional[List[Any]] = None
    # Type: CreatePort
    extra_ports: Optional[List[Any]] = None
    # Type: CreateVolume
    extra_volumes: Optional[List[Any]] = None
    # Type: CreateStorageClass
    extra_storage_classes: Optional[List[Any]] = None
    # Type: CreateCustomObject
    extra_custom_objects: Optional[List[Any]] = None
    # Type: CreateCustomResourceDefinition
    extra_crds: Optional[List[Any]] = None


class K8sApp(BaseApp):
    def __init__(self) -> None:
        super().__init__()

        # Args for the K8sApp, updated by the subclass
        self.args: K8sAppArgs = K8sAppArgs()

        # Dict of KubernetesResourceGroups
        # Type: Optional[Dict[str, K8sResourceGroup]]
        self.k8s_resource_groups: Optional[Dict[str, Any]] = None

    @property
    def container_name(self) -> str:
        from phidata.utils.k8s import get_default_container_name

        return (
            self.args.container_name
            if self.args.container_name
            else get_default_container_name(self.name)
        )

    @container_name.setter
    def container_name(self, container_name: str) -> None:
        if self.args is not None and container_name is not None:
            self.args.container_name = container_name

    @property
    def pod_name(self) -> str:
        from phidata.utils.k8s import get_default_pod_name

        return (
            self.args.pod_name
            if self.args.pod_name
            else get_default_pod_name(self.name)
        )

    @pod_name.setter
    def pod_name(self, pod_name: str) -> None:
        if self.args is not None and pod_name is not None:
            self.args.pod_name = pod_name

    @property
    def secret_name(self) -> str:
        from phidata.utils.k8s import get_default_secret_name

        return (
            self.args.secret_name
            if self.args.secret_name
            else get_default_secret_name(self.name)
        )

    @secret_name.setter
    def secret_name(self, secret_name: str) -> None:
        if self.args is not None and secret_name is not None:
            self.args.secret_name = secret_name

    @property
    def configmap_name(self) -> str:
        from phidata.utils.k8s import get_default_configmap_name

        return (
            self.args.configmap_name
            if self.args.configmap_name
            else get_default_configmap_name(self.name)
        )

    @configmap_name.setter
    def configmap_name(self, configmap_name: str) -> None:
        if self.args is not None and configmap_name is not None:
            self.args.configmap_name = configmap_name

    @property
    def deploy_name(self) -> str:
        from phidata.utils.k8s import get_default_deploy_name

        return (
            self.args.deploy_name
            if self.args.deploy_name
            else get_default_deploy_name(self.name)
        )

    @deploy_name.setter
    def deploy_name(self, deploy_name: str) -> None:
        if self.args is not None and deploy_name is not None:
            self.args.deploy_name = deploy_name

    @property
    def service_name(self) -> str:
        from phidata.utils.k8s import get_default_service_name

        return (
            self.args.service_name
            if self.args.service_name
            else get_default_service_name(self.name)
        )

    @service_name.setter
    def service_name(self, service_name: str) -> None:
        if self.args is not None and service_name is not None:
            self.args.service_name = service_name

    @property
    def service_port(self) -> int:
        return self.args.service_port

    @service_port.setter
    def service_port(self, service_port: int) -> None:
        if self.args is not None and service_port is not None:
            self.args.service_port = service_port

    @property
    def sa_name(self) -> str:
        from phidata.utils.k8s import get_default_sa_name

        return (
            self.args.sa_name if self.args.sa_name else get_default_sa_name(self.name)
        )

    @sa_name.setter
    def sa_name(self, sa_name: str) -> None:
        if self.args is not None and sa_name is not None:
            self.args.sa_name = sa_name

    @property
    def cr_name(self) -> str:
        from phidata.utils.k8s import get_default_cr_name

        return (
            self.args.cr_name if self.args.cr_name else get_default_cr_name(self.name)
        )

    @cr_name.setter
    def cr_name(self, cr_name: str) -> None:
        if self.args is not None and cr_name is not None:
            self.args.cr_name = cr_name

    @property
    def crb_name(self) -> str:
        from phidata.utils.k8s import get_default_crb_name

        return (
            self.args.crb_name
            if self.args.crb_name
            else get_default_crb_name(self.name)
        )

    @crb_name.setter
    def crb_name(self, crb_name: str) -> None:
        if self.args is not None and crb_name is not None:
            self.args.crb_name = crb_name

    def init_k8s_resource_groups(self, k8s_build_context: Any) -> None:
        logger.debug(f"@init_docker_resource_groups not defined for {self.name}")

    def get_k8s_resource_groups(
        self, k8s_build_context: Any
    ) -> Optional[Dict[str, Any]]:
        if self.k8s_resource_groups is None:
            self.init_k8s_resource_groups(k8s_build_context)
        # # Comment out in production
        # if self.k8s_resource_groups:
        #     logger.debug("K8sResourceGroups:")
        #     for rg_name, rg in self.k8s_resource_groups.items():
        #         logger.debug(
        #             "{}:{}\n{}".format(rg_name, type(rg), rg)
        #         )
        return self.k8s_resource_groups

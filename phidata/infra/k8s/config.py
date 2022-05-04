from pathlib import Path
from typing import List, Optional, Dict

from phidata.app import PhidataApp
from phidata.app.databox import default_databox_name
from phidata.infra.aws.resource.eks.cluster import EksCluster
from phidata.infra.base import InfraConfig
from phidata.infra.k8s.args import K8sArgs
from phidata.infra.k8s.manager import K8sManager
from phidata.infra.k8s.resource.group import K8sResourceGroup
from phidata.infra.k8s.create.group import CreateK8sResourceGroup
from phidata.utils.log import logger


class K8sConfig(InfraConfig):
    def __init__(
        self,
        name: Optional[str] = None,
        env: Optional[str] = None,
        version: Optional[str] = None,
        enabled: bool = True,
        namespace: str = "default",
        context: Optional[str] = None,
        service_account_name: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        apps: Optional[List[PhidataApp]] = None,
        resources: Optional[List[K8sResourceGroup]] = None,
        create_resources: Optional[List[CreateK8sResourceGroup]] = None,
        resources_dir: str = "k8s",
        databox_name: str = default_databox_name,
        kubeconfig: Optional[str] = None,
        # Get K8s context and kubeconfig from EksCluster
        eks_cluster: Optional[EksCluster] = None,
    ):
        super().__init__()
        try:
            k8s_context = context
            k8s_kubeconfig_path = Path(kubeconfig) if kubeconfig is not None else None
            if eks_cluster is not None:
                # logger.debug("Using EksCluster for K8sConfig")
                k8s_context = eks_cluster.get_kubeconfig_context_name()
                k8s_kubeconfig_path = eks_cluster.kubeconfig_path

            self.args: K8sArgs = K8sArgs(
                name=name,
                env=env,
                version=version,
                enabled=enabled,
                namespace=namespace,
                context=k8s_context,
                service_account_name=service_account_name,
                labels=labels,
                apps=apps,
                resources=resources,
                create_resources=create_resources,
                databox_name=databox_name,
                resources_dir=resources_dir,
                kubeconfig_path=k8s_kubeconfig_path,
                eks_cluster=eks_cluster,
            )
        except Exception as e:
            raise

    @property
    def namespace(self) -> Optional[str]:
        if self.args and self.args.namespace:
            return self.args.namespace
        return None

    @property
    def context(self) -> Optional[str]:
        if self.args and self.args.context:
            return self.args.context
        return None

    @property
    def service_account_name(self) -> Optional[str]:
        if self.args and self.args.service_account_name:
            return self.args.service_account_name
        return None

    @property
    def labels(self) -> Optional[Dict[str, str]]:
        if self.args and self.args.labels:
            return self.args.labels
        return None

    @property
    def apps(self) -> Optional[List[PhidataApp]]:
        if self.args and self.args.apps:
            return self.args.apps
        return None

    @property
    def resources(self) -> Optional[List[K8sResourceGroup]]:
        if self.args and self.args.resources:
            return self.args.resources
        return None

    @property
    def create_resources(self) -> Optional[List[CreateK8sResourceGroup]]:
        if self.args and self.args.create_resources:
            return self.args.create_resources
        return None

    @property
    def resources_dir(self) -> Optional[str]:
        if self.args and self.args.resources_dir:
            return self.args.resources_dir
        return None

    @property
    def databox_name(self) -> Optional[str]:
        if self.args and self.args.databox_name:
            return self.args.databox_name
        return None

    @property
    def kubeconfig_path(self) -> Optional[Path]:
        if self.args and self.args.kubeconfig_path:
            return self.args.kubeconfig_path
        return None

    @property
    def eks_cluster(self) -> Optional[EksCluster]:
        if self.args and self.args.eks_cluster:
            return self.args.eks_cluster
        return None

    def apps_are_valid(self) -> bool:
        if self.apps is None:
            return True
        for _app in self.apps:
            if not isinstance(_app, PhidataApp):
                raise TypeError("Invalid App: {}".format(_app))
        return True

    def resources_are_valid(self) -> bool:
        if self.resources is None:
            return True
        for _resource in self.resources:
            if not isinstance(_resource, K8sResourceGroup):
                raise TypeError("Invalid K8sResourceGroup: {}".format(_resource))
        return True

    def create_resources_are_valid(self) -> bool:
        if self.create_resources is None:
            return True
        for _resource in self.create_resources:
            if not isinstance(_resource, CreateK8sResourceGroup):
                raise TypeError("Invalid CreateK8sResourceGroup: {}".format(_resource))
        return True

    def is_valid(self) -> bool:
        return (
            self.apps_are_valid()
            and self.resources_are_valid()
            and self.create_resources_are_valid()
        )

    def get_k8s_manager(self) -> Optional[K8sManager]:
        return K8sManager(k8s_args=self.args)

    def get_app_by_name(self, app_name: str) -> Optional[PhidataApp]:

        if self.apps is None:
            return None

        for _app in self.apps:
            try:
                if app_name == _app.name:
                    return _app
            except Exception:
                continue
        return None

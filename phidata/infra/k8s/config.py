from pathlib import Path
from typing import List, Optional, Dict, Any

from phidata.app.phidata_app import PhidataApp
from phidata.app.databox import default_databox_name
from phidata.infra.base import InfraConfig
from phidata.infra.k8s.args import K8sArgs
from phidata.infra.k8s.manager import K8sManager
from phidata.infra.k8s.resource.group import K8sResourceGroup
from phidata.infra.k8s.create.group import CreateK8sResourceGroup
from phidata.utils.log import logger


class K8sConfig(InfraConfig):
    def __init__(
        self,
        env: Optional[str] = "prd",
        version: Optional[str] = None,
        enabled: bool = True,
        # K8s namespace to use
        namespace: str = "default",
        # K8s context to use
        context: Optional[str] = None,
        # K8s service account to use
        service_account_name: Optional[str] = None,
        # Common K8s labels to add to all resources
        common_labels: Optional[Dict[str, str]] = None,
        # PhidataApp to deploy
        apps: Optional[List[PhidataApp]] = None,
        # K8sResourceGroup to deploy
        resources: Optional[List[K8sResourceGroup]] = None,
        # CreateK8sResourceGroup to deploy
        create_resources: Optional[List[CreateK8sResourceGroup]] = None,
        # Resources dir where k8s manifests are stored
        resources_dir: str = "k8s",
        # databox name for `phi dx ...` commands
        databox_name: str = default_databox_name,
        kubeconfig: Optional[str] = None,
        # Get K8s context and kubeconfig from an EksCluster resource
        eks_cluster: Optional[Any] = None,
        # Aws params for this Config
        # Override the aws params from WorkspaceConfig if provided
        aws_region: Optional[str] = None,
        aws_profile: Optional[str] = None,
        aws_config_file: Optional[str] = None,
        aws_shared_credentials_file: Optional[str] = None,
    ):
        super().__init__()
        try:
            k8s_context = context
            k8s_kubeconfig_path = Path(kubeconfig) if kubeconfig is not None else None
            if eks_cluster is not None:
                from phidata.infra.aws.resource.eks.cluster import EksCluster

                if not isinstance(eks_cluster, EksCluster):
                    raise TypeError("eks_cluster not of type EksCluster")

                k8s_context = eks_cluster.get_kubeconfig_context_name()
                k8s_kubeconfig_path = eks_cluster.kubeconfig_path

            self.args: K8sArgs = K8sArgs(
                env=env,
                version=version,
                enabled=enabled,
                namespace=namespace,
                context=k8s_context,
                service_account_name=service_account_name,
                common_labels=common_labels,
                apps=apps,
                resources=resources,
                create_resources=create_resources,
                databox_name=databox_name,
                resources_dir=resources_dir,
                kubeconfig_path=k8s_kubeconfig_path,
                eks_cluster=eks_cluster,
                aws_region=aws_region,
                aws_profile=aws_profile,
                aws_config_file=aws_config_file,
                aws_shared_credentials_file=aws_shared_credentials_file,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    @property
    def namespace(self) -> Optional[str]:
        return self.args.namespace if self.args else None

    @namespace.setter
    def namespace(self, namespace: str) -> None:
        if self.args is not None and namespace is not None:
            self.args.namespace = namespace

    @property
    def context(self) -> Optional[str]:
        return self.args.context if self.args else None

    @context.setter
    def context(self, context: str) -> None:
        if self.args is not None and context is not None:
            self.args.context = context

    @property
    def service_account_name(self) -> Optional[str]:
        return self.args.service_account_name if self.args else None

    @service_account_name.setter
    def service_account_name(self, service_account_name: str) -> None:
        if self.args is not None and service_account_name is not None:
            self.args.service_account_name = service_account_name

    @property
    def common_labels(self) -> Optional[Dict[str, str]]:
        return self.args.common_labels if self.args else None

    @common_labels.setter
    def common_labels(self, common_labels: Dict[str, str]) -> None:
        if self.args is not None and common_labels is not None:
            self.args.common_labels = common_labels

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
    def eks_cluster(self) -> Optional[Any]:
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

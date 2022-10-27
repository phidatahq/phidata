from pathlib import Path
from typing import List, Optional, Dict, Any

from pydantic import validator

from phidata.app.phidata_app import PhidataApp
from phidata.app.databox import default_databox_name
from phidata.infra.base import InfraArgs
from phidata.infra.k8s.resource.group import K8sResourceGroup
from phidata.infra.k8s.create.group import CreateK8sResourceGroup


class K8sArgs(InfraArgs):
    # K8s namespace to use
    namespace: str = "default"
    # K8s context to use
    context: Optional[str] = None
    # K8s service account to use
    service_account_name: Optional[str] = None
    # Common K8s labels to add to all resources
    common_labels: Optional[Dict[str, str]] = None
    # PhidataApp to deploy
    apps: Optional[List[PhidataApp]] = None
    # K8sResourceGroup to deploy
    resources: Optional[List[K8sResourceGroup]] = None
    # CreateK8sResourceGroup to deploy
    create_resources: Optional[List[CreateK8sResourceGroup]] = None
    # Resources dir where k8s manifests are stored
    resources_dir: str = "k8s"
    # databox name for `phi dx ...` commands
    databox_name: str = default_databox_name
    kubeconfig_path: Optional[Path] = None

    # Get K8s context and kubeconfig from an EksCluster resource
    eks_cluster: Optional[Any] = None

    @validator("apps")
    def apps_are_valid(cls, apps):
        if apps is not None:
            for _app in apps:
                if not isinstance(_app, PhidataApp):
                    raise TypeError(f"App not of type PhidataApp: {_app}")
            return apps

    @validator("eks_cluster")
    def eks_cluster_is_valid(cls, eks_cluster):
        if eks_cluster is not None:
            from phidata.infra.aws.resource.eks.cluster import EksCluster

            if not isinstance(eks_cluster, EksCluster):
                raise TypeError("eks_cluster not of type EksCluster")
            return eks_cluster

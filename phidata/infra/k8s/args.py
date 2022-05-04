from pathlib import Path
from typing import List, Optional, Dict

from pydantic import validator

from phidata.app import PhidataApp
from phidata.app.databox import default_databox_name
from phidata.infra.aws.resource.eks.cluster import EksCluster
from phidata.infra.base import InfraArgs
from phidata.infra.k8s.create.group import CreateK8sResourceGroup
from phidata.infra.k8s.resource.group import K8sResourceGroup


class K8sArgs(InfraArgs):
    # K8s namespace to use
    namespace: str = "default"
    # K8s context to use
    context: Optional[str] = None
    service_account_name: Optional[str] = None
    labels: Optional[Dict[str, str]] = None
    apps: Optional[List[PhidataApp]] = None
    resources: Optional[List[K8sResourceGroup]] = None
    create_resources: Optional[List[CreateK8sResourceGroup]] = None
    resources_dir: str = "k8s"
    databox_name: str = default_databox_name
    kubeconfig_path: Optional[Path] = None

    # Get K8s context and kubeconfig from
    eks_cluster: Optional[EksCluster] = None

    @validator("apps")
    def apps_are_valid(cls, apps):
        if apps is not None:
            for _app in apps:
                if not isinstance(_app, PhidataApp):
                    raise TypeError("App not of type PhidataApp: {}".format(_app))
            return apps

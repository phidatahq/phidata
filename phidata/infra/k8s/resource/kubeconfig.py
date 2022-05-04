import datetime
from typing import List, Optional, Any, Dict

from pydantic import BaseModel, Field

import phidata.infra.k8s.enums as k8s_enums


# Kubeconfig Cluster
class KubeconfigClusterConfig(BaseModel):
    server: str
    certificate_authority_data: str = Field(..., alias="certificate-authority-data")

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        use_enum_values = True


class KubeconfigCluster(BaseModel):
    name: str
    cluster: KubeconfigClusterConfig


class KubeconfigUser(BaseModel):
    name: str
    user: Dict[str, Any]


# Kubeconfig Context
class KubeconfigContextSpec(BaseModel):
    """Each Kubeconfig context is a triple (cluster, user, namespace). It should be read as:
    Use the credentials of the "user" to access the "namespace" of the "cluster”
    """

    cluster: Optional[str]
    user: Optional[str]
    namespace: Optional[str]


class KubeconfigContext(BaseModel):
    """A context element in a kubeconfig file is used to group access parameters under a
    convenient name. Each context has three parameters: cluster, namespace, and user.
    By default, the kubectl command-line tool uses parameters from the current context
    to communicate with the cluster.
    """

    name: str
    context: KubeconfigContextSpec


# Kubeconfig
class Kubeconfig(BaseModel):
    """This is one of the most important models, and the one we know the least about :(

    We configure access to K8s clusters using a Kubeconfig. This configuration can be stored in a file or an object.
    A Kubeconfig stores information about clusters, users, namespaces, and authentication mechanisms,

    When we use K8s locally on our machine, our kubeconfig file is usually stored at ~/.kube/config
    A file that is used to configure access to a cluster is called a kubeconfig file. This is a generic way of referring to configuration files. It does not mean that there is a file named kubeconfig.
    View your local kubeconfig using `kubectl config view`

    References:
        * Docs:
            https://kubernetes.io/docs/tasks/access-application-cluster/configure-access-multiple-clusters/
        * Go Doc: https://godoc.org/k8s.io/client-go/tools/clientcmd/api#Config
    """

    api_version: k8s_enums.ApiVersion = Field(..., alias="apiVersion")
    kind: k8s_enums.Kind
    clusters: List[KubeconfigCluster] = []
    users: List[KubeconfigUser] = []
    contexts: List[KubeconfigContext] = []
    current_context: Optional[str] = Field(None, alias="current-context")
    preferences: dict = {}

    class Config:
        allow_population_by_field_name = True
        use_enum_values = True

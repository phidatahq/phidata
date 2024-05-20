from pathlib import Path
from typing import List, Optional, Any, Dict

from pydantic import BaseModel, Field, ConfigDict

from phi.utils.log import logger


class KubeconfigClusterConfig(BaseModel):
    server: str
    certificate_authority_data: str = Field(..., alias="certificate-authority-data")

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)


class KubeconfigCluster(BaseModel):
    name: str
    cluster: KubeconfigClusterConfig


class KubeconfigUser(BaseModel):
    name: str
    user: Dict[str, Any]


class KubeconfigContextSpec(BaseModel):
    """Each Kubeconfig context is made of (cluster, user, namespace).
    It should be read as:
        Use the credentials of the "user"
        to access the "namespace"
        of the "cluster"
    """

    cluster: Optional[str]
    user: Optional[str]
    namespace: Optional[str] = None


class KubeconfigContext(BaseModel):
    """A context element in a kubeconfig file is used to group access parameters under a
    convenient name. Each context has three parameters: cluster, namespace, and user.
    By default, the kubectl command-line tool uses parameters from the current context
    to communicate with the cluster.
    """

    name: str
    context: KubeconfigContextSpec


class Kubeconfig(BaseModel):
    """
    We configure access to K8s clusters using a Kubeconfig.
    This configuration can be stored in a file or an object.
    A Kubeconfig stores information about clusters, users, namespaces, and authentication mechanisms,

    Locally the kubeconfig file is usually stored at ~/.kube/config
    View your local kubeconfig using `kubectl config view`

    References:
        * Docs:
            https://kubernetes.io/docs/tasks/access-application-cluster/configure-access-multiple-clusters/
        * Go Doc: https://godoc.org/k8s.io/client-go/tools/clientcmd/api#Config
    """

    api_version: str = Field("v1", alias="apiVersion")
    kind: str = "Config"
    clusters: List[KubeconfigCluster] = []
    users: List[KubeconfigUser] = []
    contexts: List[KubeconfigContext] = []
    current_context: Optional[str] = Field(None, alias="current-context")
    preferences: dict = {}

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    @classmethod
    def read_from_file(cls: Any, file_path: Path, create_if_not_exists: bool = True) -> Optional[Any]:
        if file_path is not None:
            if not file_path.exists():
                if create_if_not_exists:
                    logger.info(f"Creating: {file_path}")
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.touch()
                else:
                    logger.error(f"File does not exist: {file_path}")
                    return None
            if file_path.exists() and file_path.is_file():
                try:
                    import yaml

                    logger.info(f"Reading {file_path}")
                    kubeconfig_dict = yaml.safe_load(file_path.read_text())
                    if kubeconfig_dict is not None and isinstance(kubeconfig_dict, dict):
                        kubeconfig = cls(**kubeconfig_dict)
                        return kubeconfig
                except Exception as e:
                    logger.error(f"Error reading {file_path}")
                    logger.error(e)
        else:
            logger.warning(f"Kubeconfig invalid: {file_path}")
        return None

    def write_to_file(self, file_path: Path) -> bool:
        """Writes the kubeconfig to file_path"""
        if file_path is not None:
            try:
                import yaml

                kubeconfig_dict = self.model_dump(exclude_none=True, by_alias=True)
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(yaml.safe_dump(kubeconfig_dict))
                logger.info(f"Updated: {file_path}")
                return True
            except Exception as e:
                logger.error(f"Error writing {file_path}")
                logger.error(e)
        else:
            logger.error(f"Kubeconfig invalid: {file_path}")
        return False

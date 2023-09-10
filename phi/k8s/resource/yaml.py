from pathlib import Path
from typing import Optional, Any

from phi.k8s.api_client import K8sApiClient
from phi.k8s.enums.api_version import ApiVersion
from phi.k8s.enums.kind import Kind
from phi.k8s.resource.base import K8sResource
from phi.k8s.resource.meta.v1.object_meta import ObjectMeta


class YamlResource(K8sResource):
    resource_type: str = "Yaml"

    api_version: ApiVersion = ApiVersion.NA
    kind: Kind = Kind.YAML
    metadata: ObjectMeta = ObjectMeta()

    file: Optional[Path] = None
    dir: Optional[Path] = None
    url: Optional[str] = None

    @staticmethod
    def get_from_cluster(k8s_client: K8sApiClient, namespace: Optional[str] = None, **kwargs) -> None:
        # Not implemented for YamlResources
        return None

    def _create(self, k8s_client: K8sApiClient) -> bool:
        return True

    def _read(self, k8s_client: K8sApiClient) -> Optional[Any]:
        return None

    def _update(self, k8s_client: K8sApiClient) -> bool:
        return True

    def _delete(self, k8s_client: K8sApiClient) -> bool:
        return True

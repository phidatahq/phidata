from typing import Optional

from kubernetes.client.models.v1_object_reference import V1ObjectReference
from pydantic import Field

from phi.k8s.resource.base import K8sResource


class ObjectReference(K8sResource):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/objectreference-v1-core
    """

    resource_type: str = "ObjectReference"

    # Name of the referent. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names
    name: str
    # Namespace of the referent.
    # More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/namespaces/
    namespace: str
    # Specific resourceVersion to which this reference is made, if any.
    # More info:
    # https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#concurrency-control-and-consistency
    resource_version: Optional[str] = Field(None, alias="resourceVersion")
    # UID of the referent. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#uids
    uid: Optional[str] = None

    def get_k8s_object(self) -> V1ObjectReference:
        # Return a V1ObjectReference object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_object_reference.py
        _v1_object_reference = V1ObjectReference(
            api_version=self.api_version.value,
            kind=self.kind.value,
            name=self.name,
            namespace=self.namespace,
            resource_version=self.resource_version,
            uid=self.uid,
        )
        return _v1_object_reference

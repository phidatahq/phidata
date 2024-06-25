from kubernetes.client.models.v1_local_object_reference import V1LocalObjectReference

from phi.k8s.resource.base import K8sObject


class LocalObjectReference(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#localobjectreference-v1-core
    """

    resource_type: str = "LocalObjectReference"

    # Name of the referent. More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names
    name: str

    def get_k8s_object(self) -> V1LocalObjectReference:
        # Return a V1LocalObjectReference object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_local_object_reference.py
        _v1_local_object_reference = V1LocalObjectReference(name=self.name)
        return _v1_local_object_reference

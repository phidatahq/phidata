from kubernetes.client.models.v1_pod_template_spec import V1PodTemplateSpec

from phidata.infra.k8s.resource.base import K8sObject
from phidata.infra.k8s.resource.core.v1.pod_spec import PodSpec
from phidata.infra.k8s.resource.meta.v1.object_meta import ObjectMeta


class PodTemplateSpec(K8sObject):
    """
    # https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#podtemplatespec-v1-core
    """

    resource_type: str = "PodTemplateSpec"

    metadata: ObjectMeta
    spec: PodSpec

    def get_k8s_object(self) -> V1PodTemplateSpec:

        # Set and return a V1PodTemplateSpec object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_pod_template_spec.py
        _v1_pod_template_spec = V1PodTemplateSpec(
            metadata=self.metadata.get_k8s_object(),
            spec=self.spec.get_k8s_object(),
        )
        return _v1_pod_template_spec

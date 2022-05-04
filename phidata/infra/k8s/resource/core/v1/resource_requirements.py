from typing import Dict, Optional

from kubernetes.client.models.v1_resource_requirements import V1ResourceRequirements

from phidata.infra.k8s.resource.base import K8sObject


class ResourceRequirements(K8sObject):
    """
    ResourceRequirements describes the compute resource requirements.

    # https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#resourcerequirements-v1-core
    """

    resource_type: str = "ResourceRequirements"

    # Limits describes the maximum amount of compute resources allowed
    limits: Optional[Dict[str, str]] = None
    # Requests describes the minimum amount of compute resources required.
    # If Requests is omitted for a container, it defaults to Limits if that is explicitly specified,
    # otherwise to an implementation-defined value.
    requests: Optional[Dict[str, str]] = None

    def get_k8s_object(self) -> V1ResourceRequirements:

        # Return a V1ResourceRequirements object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_resource_requirements.py
        _v1_resource_requirements = V1ResourceRequirements(
            limits=self.limits,
            requests=self.requests,
        )
        return _v1_resource_requirements

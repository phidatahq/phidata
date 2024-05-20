from typing import Optional

from pydantic import Field
from kubernetes.client.models.v1_toleration import V1Toleration

from phi.k8s.resource.base import K8sObject


class Toleration(K8sObject):
    """
    The pod this Toleration is attached to tolerates any taint that matches
    the triple <key,value,effect> using the matching operator <operator>.

    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#toleration-v1-core
    """

    resource_type: str = "Toleration"

    # Effect indicates the taint effect to match.
    # Empty means match all taint effects.
    # When specified, allowed values are NoSchedule, PreferNoSchedule and NoExecute.
    effect: Optional[str] = None
    # Key is the taint key that the toleration applies to. Empty means match all taint keys.
    # If the key is empty, operator must be Exists; this combination means to match all values and all keys.
    key: Optional[str] = None
    # Operator represents a key's relationship to the value. Valid operators are Exists and Equal. Defaults to Equal.
    # Exists is equivalent to wildcard for value, so that a pod can tolerate all taints of a particular category.
    # Possible enum values: - `"Equal"` - `"Exists"`
    operator: Optional[str] = None
    # TolerationSeconds represents the period of time the toleration (which must be of effect NoExecute,
    # otherwise this field is ignored) tolerates the taint. By default, it is not set, which means tolerate the
    # taint forever (do not evict). Zero and negative values will be treated as 0 (evict immediately) by the system.
    toleration_seconds: Optional[int] = Field(None, alias="tolerationSeconds")
    # Value is the taint value the toleration matches to. If the operator is Exists, the value should be empty,
    # otherwise just a regular string.
    value: Optional[str] = None

    def get_k8s_object(self) -> V1Toleration:
        # Return a V1Toleration object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_toleration.py
        _v1_toleration = V1Toleration(
            effect=self.effect,
            key=self.key,
            operator=self.operator,
            toleration_seconds=self.toleration_seconds,
            value=self.value,
        )
        return _v1_toleration

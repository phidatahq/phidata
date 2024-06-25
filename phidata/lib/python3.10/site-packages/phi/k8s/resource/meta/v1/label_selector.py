from typing import Dict, Optional

from kubernetes.client.models.v1_label_selector import V1LabelSelector
from pydantic import Field

from phi.k8s.resource.base import K8sObject


class LabelSelector(K8sObject):
    """
    A label selector is a label query over a set of resources.
    The result of matchLabels and matchExpressions are ANDed.
    An empty label selector matches all objects.
    A null label selector matches no objects.

    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#labelselector-v1-meta
    """

    resource_type: str = "LabelSelector"

    # matchLabels is a map of {key,value} pairs.
    match_labels: Optional[Dict[str, str]] = Field(None, alias="matchLabels")

    def get_k8s_object(self) -> V1LabelSelector:
        # Return a V1LabelSelector object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_label_selector.py
        _v1_label_selector = V1LabelSelector(
            match_labels=self.match_labels,
        )
        return _v1_label_selector

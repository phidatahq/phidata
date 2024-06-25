from typing import List, Optional

from kubernetes.client.models.v1_node_selector import V1NodeSelector
from kubernetes.client.models.v1_node_selector_term import V1NodeSelectorTerm
from kubernetes.client.models.v1_node_selector_requirement import (
    V1NodeSelectorRequirement,
)
from pydantic import Field

from phi.k8s.resource.base import K8sObject


class NodeSelectorRequirement(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#nodeselectorrequirement-v1-core
    """

    resource_type: str = "NodeSelectorRequirement"

    # The label key that the selector applies to.
    key: str
    # Represents a key's relationship to a set of values.
    # Valid operators are In, NotIn, Exists, DoesNotExist. Gt, and Lt.
    # Possible enum values: - `"DoesNotExist"` - `"Exists"` - `"Gt"` - `"In"` - `"Lt"` - `"NotIn"`
    operator: str
    # An array of string values. If the operator is In or NotIn, the values array must be non-empty.
    # If the operator is Exists or DoesNotExist, the values array must be empty.
    # If the operator is Gt or Lt, the values array must have a single element, which will be interpreted as an integer.
    # This array is replaced during a strategic merge patch.
    values: Optional[List[str]]

    def get_k8s_object(
        self,
    ) -> V1NodeSelectorRequirement:
        # Return a V1NodeSelectorRequirement object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_node_selector_requirement.py
        _v1_node_selector_requirement = V1NodeSelectorRequirement(
            key=self.key,
            operator=self.operator,
            values=self.values,
        )
        return _v1_node_selector_requirement


class NodeSelectorTerm(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#nodeselectorterm-v1-core
    """

    resource_type: str = "NodeSelectorTerm"

    # A list of node selector requirements by node's labels.
    match_expressions: Optional[List[NodeSelectorRequirement]] = Field(..., alias="matchExpressions")
    # A list of node selector requirements by node's fields.
    match_fields: Optional[List[NodeSelectorRequirement]] = Field(..., alias="matchFields")

    def get_k8s_object(
        self,
    ) -> V1NodeSelectorTerm:
        # Return a V1NodeSelectorTerm object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_node_selector_term.py
        _v1_node_selector_term = V1NodeSelectorTerm(
            match_expressions=[me.get_k8s_object() for me in self.match_expressions]
            if self.match_expressions
            else None,
            match_fields=[mf.get_k8s_object() for mf in self.match_fields] if self.match_fields else None,
        )
        return _v1_node_selector_term


class NodeSelector(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#nodeselector-v1-core
    """

    resource_type: str = "NodeSelector"

    # A node selector represents the union of the results of one or more label queries over a set of nodes;
    # that is, it represents the OR of the selectors represented by the node selector terms.
    node_selector_terms: List[NodeSelectorTerm] = Field(..., alias="nodeSelectorTerms")

    def get_k8s_object(
        self,
    ) -> V1NodeSelector:
        # Return a V1NodeSelector object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_node_selector.py
        _v1_node_selector = V1NodeSelector(
            node_selector_terms=[nst.get_k8s_object() for nst in self.node_selector_terms]
            if self.node_selector_terms
            else None,
        )
        return _v1_node_selector

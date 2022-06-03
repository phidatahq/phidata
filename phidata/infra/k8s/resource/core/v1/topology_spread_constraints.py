from typing import Optional
from typing_extensions import Literal

from pydantic import Field
from kubernetes.client.models.v1_topology_spread_constraint import (
    V1TopologySpreadConstraint,
)

from phidata.infra.k8s.resource.meta.v1.label_selector import LabelSelector
from phidata.infra.k8s.resource.base import K8sObject


class TopologySpreadConstraint(K8sObject):
    """
    TopologySpreadConstraint specifies how to spread matching pods among the given topology.

    # https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#topologyspreadconstraint-v1-core
    """

    resource_type: str = "TopologySpreadConstraint"

    # LabelSelector is used to find matching pods. Pods that match this label selector are counted
    # to determine the number of pods in their corresponding topology domain.
    label_selector: Optional[LabelSelector] = Field(None, alias="labelSelector")
    # MaxSkew describes the degree to which pods may be unevenly distributed.
    # When `whenUnsatisfiable=DoNotSchedule`, it is the maximum permitted difference between the number of matching
    # pods in the target topology and the global minimum.
    # For example, in a 3-zone cluster, MaxSkew is set to 1, and pods with the same labelSelector
    # spread as 1/1/0: | zone1 | zone2 | zone3 | | P | P | | - if MaxSkew is 1, incoming pod can only be scheduled to
    # zone3 to become 1/1/1; scheduling it onto zone1(zone2) would make the ActualSkew(2-0) on zone1(zone2)
    # violate MaxSkew(1). - if MaxSkew is 2, incoming pod can be scheduled onto any zone.
    # When `whenUnsatisfiable=ScheduleAnyway`, it is used to give higher precedence to topologies that satisfy it.
    # It's a required field.
    # Default value is 1 and 0 is not allowed.
    max_skew: Optional[int] = Field(None, alias="maxSkew")
    # TopologyKey is the key of node labels.
    # Nodes that have a label with this key and identical values are considered to be in the same topology.
    # We consider each <key, value> as a "bucket", and try to put balanced number of pods into each bucket.
    # It's a required field.
    topology_key: Optional[str] = Field(None, alias="topologyKey")
    # WhenUnsatisfiable indicates how to deal with a pod if it doesn't satisfy the spread constraint.
    # - DoNotSchedule (default) tells the scheduler not to schedule it.
    # - ScheduleAnyway tells the scheduler to schedule the pod in any location, but giving higher precedence
    # to topologies that would help reduce the skew.
    # A constraint is considered "Unsatisfiable" for an incoming pod if and only if every possible node assignment
    # for that pod would violate "MaxSkew" on some topology.
    # For example, in a 3-zone cluster, MaxSkew is set to 1, and pods with the same labelSelector
    # spread as 3/1/1: | zone1 | zone2 | zone3 | | P P P | P | P |
    # If WhenUnsatisfiable is set to DoNotSchedule, incoming pod can only be scheduled to
    # zone2(zone3) to become 3/2/1(3/1/2) as ActualSkew(2-1) on zone2(zone3) satisfies MaxSkew(1).
    # In other words, the cluster can still be imbalanced, but scheduler won't make it *more* imbalanced.
    # It's a required field. Possible enum values: - `"DoNotSchedule"` instructs the scheduler not to schedule the
    # pod when constraints are not satisfied.
    # - `"ScheduleAnyway"` instructs the scheduler to schedule the pod even if constraints are not satisfied.
    when_unsatisfiable: Optional[Literal["DoNotSchedule", "ScheduleAnyway"]] = Field(
        None, alias="whenUnsatisfiable"
    )

    def get_k8s_object(self) -> V1TopologySpreadConstraint:

        # Return a V1TopologySpreadConstraint object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_topology_spread_constraint.py
        _v1_topology_spread_constraint = V1TopologySpreadConstraint(
            label_selector=self.label_selector,
            max_skew=self.max_skew,
            topology_key=self.topology_key,
            when_unsatisfiable=self.when_unsatisfiable,
        )
        return _v1_topology_spread_constraint

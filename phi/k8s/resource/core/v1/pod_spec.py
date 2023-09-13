from typing import List, Optional, Any, Dict

from pydantic import Field, field_serializer

from kubernetes.client.models.v1_container import V1Container
from kubernetes.client.models.v1_pod_spec import V1PodSpec
from kubernetes.client.models.v1_volume import V1Volume

from phi.k8s.enums.restart_policy import RestartPolicy
from phi.k8s.resource.base import K8sObject
from phi.k8s.resource.core.v1.container import Container
from phi.k8s.resource.core.v1.toleration import Toleration
from phi.k8s.resource.core.v1.topology_spread_constraints import (
    TopologySpreadConstraint,
)
from phi.k8s.resource.core.v1.local_object_reference import (
    LocalObjectReference,
)
from phi.k8s.resource.core.v1.volume import Volume


class PodSpec(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#podspec-v1-core
    """

    resource_type: str = "PodSpec"

    # Optional duration in seconds the pod may be active on the node relative to StartTime before
    # the system will actively try to mark it failed and kill associated containers.
    # Value must be a positive integer.
    active_deadline_seconds: Optional[int] = Field(None, alias="activeDeadlineSeconds")
    # If specified, the pod's scheduling constraints
    # TODO: create affinity object
    affinity: Optional[Any] = None
    # AutomountServiceAccountToken indicates whether a service account token should be automatically mounted.
    automount_service_account_token: Optional[bool] = Field(None, alias="automountServiceAccountToken")
    # List of containers belonging to the pod. Containers cannot currently be added or removed.
    # There must be at least one container in a Pod. Cannot be updated.
    containers: List[Container]
    # Specifies the DNS parameters of a pod.
    # Parameters specified here will be merged to the generated DNS configuration based on DNSPolicy.
    # TODO: create dns_config object
    dns_config: Optional[Any] = Field(None, alias="dnsConfig")
    dns_policy: Optional[str] = Field(None, alias="dnsPolicy")
    # ImagePullSecrets is an optional list of references to secrets in the same namespace to
    # use for pulling any of the images used by this PodSpec.
    # If specified, these secrets will be passed to individual puller implementations for them to use.
    # For example, in the case of docker, only DockerConfig type secrets are honored.
    # More info: https://kubernetes.io/docs/concepts/containers/images#specifying-imagepullsecrets-on-a-pod
    image_pull_secrets: Optional[List[LocalObjectReference]] = Field(None, alias="imagePullSecrets")
    # List of initialization containers belonging to the pod.
    # Init containers are executed in order prior to containers being started.
    # If any init container fails, the pod is considered to have failed and is
    # handled according to its restartPolicy.
    # The name for an init container or normal container must be unique among all containers.
    # Init containers may not have Lifecycle actions, Readiness probes, Liveness probes, or Startup probes.
    # The resourceRequirements of an init container are taken into account during scheduling by finding
    # the highest request/limit for each resource type, and then using the max of that value or
    # the sum of the normal containers. Limits are applied to init containers in a similar fashion.
    # Init containers cannot currently be added or removed. Cannot be updated.
    # More info: https://kubernetes.io/docs/concepts/workloads/pods/init-containers/
    init_containers: Optional[List[Container]] = Field(None, alias="initContainers")
    # NodeName is a request to schedule this pod onto a specific node.
    # If it is non-empty, the scheduler simply schedules this pod onto that node,
    # assuming that it fits resource requirements.
    node_name: Optional[str] = Field(None, alias="nodeName")
    # NodeSelector is a selector which must be true for the pod to fit on a node.
    # Selector which must match a node's labels for the pod to be scheduled on that node.
    # More info: https://kubernetes.io/docs/concepts/configuration/assign-pod-node/
    node_selector: Optional[Dict[str, str]] = Field(None, alias="nodeSelector")
    # Restart policy for all containers within the pod.
    # One of Always, OnFailure, Never. Default to Always.
    # More info: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#restart-policy
    restart_policy: Optional[RestartPolicy] = Field(None, alias="restartPolicy")
    # ServiceAccountName is the name of the ServiceAccount to use to run this pod.
    # More info: https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/
    service_account_name: Optional[str] = Field(None, alias="serviceAccountName")
    termination_grace_period_seconds: Optional[int] = Field(None, alias="terminationGracePeriodSeconds")
    # If specified, the pod's tolerations.
    tolerations: Optional[List[Toleration]] = None
    # TopologySpreadConstraints describes how a group of pods ought to spread across topology domains.
    # Scheduler will schedule pods in a way which abides by the constraints.
    # All topologySpreadConstraints are ANDed.
    topology_spread_constraints: Optional[List[TopologySpreadConstraint]] = Field(
        None, alias="topologySpreadConstraints"
    )
    # List of volumes that can be mounted by containers belonging to the pod.
    # More info: https://kubernetes.io/docs/concepts/storage/volumes
    volumes: Optional[List[Volume]] = None

    @field_serializer("restart_policy")
    def get_restart_policy_value(self, v) -> Optional[str]:
        return v.value if v is not None else None

    def get_k8s_object(self) -> V1PodSpec:
        # Set and return a V1PodSpec object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_pod_spec.py

        _containers: Optional[List[V1Container]] = None
        if self.containers:
            _containers = []
            for _container in self.containers:
                _containers.append(_container.get_k8s_object())

        _init_containers: Optional[List[V1Container]] = None
        if self.init_containers:
            _init_containers = []
            for _init_container in self.init_containers:
                _init_containers.append(_init_container.get_k8s_object())

        _image_pull_secrets = None
        if self.image_pull_secrets:
            _image_pull_secrets = []
            for ips in self.image_pull_secrets:
                _image_pull_secrets.append(ips.get_k8s_object())

        _volumes: Optional[List[V1Volume]] = None
        if self.volumes:
            _volumes = []
            for _volume in self.volumes:
                _volumes.append(_volume.get_k8s_object())

        _v1_pod_spec = V1PodSpec(
            active_deadline_seconds=self.active_deadline_seconds,
            affinity=self.affinity,
            automount_service_account_token=self.automount_service_account_token,
            containers=_containers,
            dns_config=self.dns_config,
            dns_policy=self.dns_policy,
            image_pull_secrets=_image_pull_secrets,
            init_containers=_init_containers,
            node_name=self.node_name,
            node_selector=self.node_selector,
            restart_policy=self.restart_policy.value if self.restart_policy else None,
            service_account_name=self.service_account_name,
            termination_grace_period_seconds=self.termination_grace_period_seconds,
            volumes=_volumes,
        )
        return _v1_pod_spec

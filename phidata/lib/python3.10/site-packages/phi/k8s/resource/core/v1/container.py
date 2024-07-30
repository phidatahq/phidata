from typing import Any, List, Optional

from pydantic import Field, field_serializer

from kubernetes.client.models.v1_config_map_env_source import V1ConfigMapEnvSource
from kubernetes.client.models.v1_config_map_key_selector import V1ConfigMapKeySelector
from kubernetes.client.models.v1_container import V1Container
from kubernetes.client.models.v1_container_port import V1ContainerPort
from kubernetes.client.models.v1_env_from_source import V1EnvFromSource
from kubernetes.client.models.v1_env_var import V1EnvVar
from kubernetes.client.models.v1_env_var_source import V1EnvVarSource
from kubernetes.client.models.v1_object_field_selector import V1ObjectFieldSelector
from kubernetes.client.models.v1_probe import V1Probe
from kubernetes.client.models.v1_resource_field_selector import V1ResourceFieldSelector
from kubernetes.client.models.v1_secret_env_source import V1SecretEnvSource
from kubernetes.client.models.v1_secret_key_selector import V1SecretKeySelector
from kubernetes.client.models.v1_volume_mount import V1VolumeMount

from phi.k8s.enums.image_pull_policy import ImagePullPolicy
from phi.k8s.enums.protocol import Protocol
from phi.k8s.resource.base import K8sObject
from phi.k8s.resource.core.v1.resource_requirements import (
    ResourceRequirements,
)


class Probe(K8sObject):
    """
    Probe describes a health check to be performed against a container to determine whether it is ready for traffic.

    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#probe-v1-core
    """

    resource_type: str = "Probe"

    # Minimum consecutive failures for the probe to be considered failed after having succeeded.
    # Defaults to 3. Minimum value is 1.
    failure_threshold: Optional[int] = Field(None, alias="failureThreshold")
    # GRPC specifies an action involving a GRPC port. This is an alpha field and requires enabling
    # GRPCContainerProbe feature gate.
    grpc: Optional[Any] = None
    # HTTPGet specifies the http request to perform.
    http_get: Optional[Any] = Field(None, alias="httpGet")
    # Number of seconds after the container has started before liveness probes are initiated.
    # More info: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle#container-probes
    initial_delay_seconds: Optional[int] = Field(None, alias="initialDelaySeconds")
    # How often (in seconds) to perform the probe. Default to 10 seconds. Minimum value is 1.
    period_seconds: Optional[int] = Field(None, alias="periodSeconds")
    # Minimum consecutive successes for the probe to be considered successful after having failed.
    # Defaults to 1. Must be 1 for liveness and startup. Minimum value is 1.
    success_threshold: Optional[int] = Field(None, alias="successThreshold")
    # TCPSocket specifies an action involving a TCP port.
    tcp_socket: Optional[Any] = Field(None, alias="tcpSocket")
    # Optional duration in seconds the pod needs to terminate gracefully upon probe failure.
    # The grace period is the duration in seconds after the processes running in the pod are sent a termination signal
    # and the time when the processes are forcibly halted with a kill signal. Set this value longer than the expected
    # cleanup time for your process. If this value is nil, the pod's terminationGracePeriodSeconds will be used.
    # Otherwise, this value overrides the value provided by the pod spec. Value must be non-negative integer.
    # The value zero indicates stop immediately via the kill signal (no opportunity to shut down).
    # This is a beta field and requires enabling ProbeTerminationGracePeriod feature gate.
    # Minimum value is 1. spec.terminationGracePeriodSeconds is used if unset.
    termination_grace_period_seconds: Optional[int] = Field(None, alias="terminationGracePeriodSeconds")
    # Number of seconds after which the probe times out. Defaults to 1 second. Minimum value is 1.
    # More info: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle#container-probes
    timeout_seconds: Optional[int] = Field(None, alias="timeoutSeconds")

    def get_k8s_object(self) -> V1Probe:
        _v1_probe = V1Probe(
            failure_threshold=self.failure_threshold,
            http_get=self.http_get,
            initial_delay_seconds=self.initial_delay_seconds,
            period_seconds=self.period_seconds,
            success_threshold=self.success_threshold,
            tcp_socket=self.tcp_socket,
            termination_grace_period_seconds=self.termination_grace_period_seconds,
            timeout_seconds=self.timeout_seconds,
        )
        return _v1_probe


class ResourceFieldSelector(K8sObject):
    """
    ResourceFieldSelector represents container resources (cpu, memory) and their output format

    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#resourcefieldselector-v1-core
    """

    resource_type: str = "ResourceFieldSelector"

    container_name: str = Field(..., alias="containerName")
    divisor: str
    resource: str

    def get_k8s_object(self) -> V1ResourceFieldSelector:
        # Return a V1ResourceFieldSelector object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_resource_field_selector.py
        _v1_resource_field_selector = V1ResourceFieldSelector(
            container_name=self.container_name,
            divisor=self.divisor,
            resource=self.resource,
        )
        return _v1_resource_field_selector


class ObjectFieldSelector(K8sObject):
    """
    ObjectFieldSelector selects an APIVersioned field of an object.

    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#objectfieldselector-v1-core
    """

    resource_type: str = "ObjectFieldSelector"

    api_version: str = Field(..., alias="apiVersion")
    field_path: str = Field(..., alias="fieldPath")

    def get_k8s_object(self) -> V1ObjectFieldSelector:
        # Return a V1ObjectFieldSelector object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_object_field_selector.py
        _v1_object_field_selector = V1ObjectFieldSelector(
            api_version=self.api_version,
            field_path=self.field_path,
        )
        return _v1_object_field_selector


class SecretKeySelector(K8sObject):
    """
    SecretKeySelector selects a key of a Secret.

    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#secretkeyselector-v1-core
    """

    resource_type: str = "SecretKeySelector"

    key: str
    name: str
    optional: Optional[bool] = None

    def get_k8s_object(self) -> V1SecretKeySelector:
        # Return a V1SecretKeySelector object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_secret_key_selector.py
        _v1_secret_key_selector = V1SecretKeySelector(
            key=self.key,
            name=self.name,
            optional=self.optional,
        )
        return _v1_secret_key_selector


class ConfigMapKeySelector(K8sObject):
    """
    Selects a key from a ConfigMap.

    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#configmapkeyselector-v1-core
    """

    resource_type: str = "ConfigMapKeySelector"

    key: str
    name: str
    optional: Optional[bool] = None

    def get_k8s_object(self) -> V1ConfigMapKeySelector:
        # Return a V1ConfigMapKeySelector object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_config_map_key_selector.py
        _v1_config_map_key_selector = V1ConfigMapKeySelector(
            key=self.key,
            name=self.name,
            optional=self.optional,
        )
        return _v1_config_map_key_selector


class EnvVarSource(K8sObject):
    """
    EnvVarSource represents a source for the value of an EnvVar.

    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#envvarsource-v1-core
    """

    resource_type: str = "EnvVarSource"

    config_map_key_ref: Optional[ConfigMapKeySelector] = Field(None, alias="configMapKeyRef")
    field_ref: Optional[ObjectFieldSelector] = Field(None, alias="fieldRef")
    resource_field_ref: Optional[ResourceFieldSelector] = Field(None, alias="resourceFieldRef")
    secret_key_ref: Optional[SecretKeySelector] = Field(None, alias="secretKeyRef")

    def get_k8s_object(self) -> V1EnvVarSource:
        # Return a V1EnvVarSource object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_env_var_source.py
        _v1_env_var_source = V1EnvVarSource(
            config_map_key_ref=self.config_map_key_ref.get_k8s_object() if self.config_map_key_ref else None,
            field_ref=self.field_ref.get_k8s_object() if self.field_ref else None,
            resource_field_ref=self.resource_field_ref.get_k8s_object() if self.resource_field_ref else None,
            secret_key_ref=self.secret_key_ref.get_k8s_object() if self.secret_key_ref else None,
        )
        return _v1_env_var_source


class EnvVar(K8sObject):
    """
    EnvVar represents an environment variable present in a Container.

    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#envvar-v1-core
    """

    resource_type: str = "EnvVar"

    name: str
    value: Optional[str] = None
    value_from: Optional[EnvVarSource] = Field(None, alias="valueFrom")

    def get_k8s_object(self) -> V1EnvVar:
        # Return a V1EnvVar object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_env_var.py
        _v1_env_var = V1EnvVar(
            name=self.name,
            value=self.value,
            value_from=self.value_from.get_k8s_object() if self.value_from else None,
        )
        return _v1_env_var


class ConfigMapEnvSource(K8sObject):
    """
    ConfigMapEnvSource selects a ConfigMap to populate the environment variables with.
    The contents of the target ConfigMap's Data field will represent the key-value pairs as environment variables.

    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#configmapenvsource-v1-core
    """

    resource_type: str = "ConfigMapEnvSource"

    name: str
    optional: Optional[bool] = None

    def get_k8s_object(self) -> V1ConfigMapEnvSource:
        _v1_config_map_env_source = V1ConfigMapEnvSource(
            name=self.name,
            optional=self.optional,
        )
        return _v1_config_map_env_source


class SecretEnvSource(K8sObject):
    """
    SecretEnvSource selects a Secret to populate the environment variables with.
    The contents of the target Secret's Data field will represent the key-value pairs as environment variables.

    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#secretenvsource-v1-core
    """

    resource_type: str = "SecretEnvSource"

    name: str
    optional: Optional[bool] = None

    def get_k8s_object(self) -> V1SecretEnvSource:
        _v1_secret_env_source = V1SecretEnvSource(
            name=self.name,
            optional=self.optional,
        )
        return _v1_secret_env_source


class EnvFromSource(K8sObject):
    """
    EnvFromSource represents the source of a set of ConfigMaps

    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#envfromsource-v1-core
    """

    resource_type: str = "EnvFromSource"

    config_map_ref: Optional[ConfigMapEnvSource] = Field(None, alias="configMapRef")
    prefix: Optional[str] = None
    secret_ref: Optional[SecretEnvSource] = Field(None, alias="secretRef")

    def get_k8s_object(self) -> V1EnvFromSource:
        # Return a V1EnvFromSource object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_env_from_source.py
        _v1_env_from_source = V1EnvFromSource(
            config_map_ref=self.config_map_ref.get_k8s_object() if self.config_map_ref else None,
            prefix=self.prefix,
            secret_ref=self.secret_ref.get_k8s_object() if self.secret_ref else None,
        )
        return _v1_env_from_source


class ContainerPort(K8sObject):
    """
    ContainerPort represents a network port in a single container.

    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#containerport-v1-core
    """

    resource_type: str = "ContainerPort"

    # If specified, this must be an IANA_SVC_NAME and unique within the pod.
    # Each named port in a pod must have a unique name.
    # Name for the port that can be referred to by services.
    name: Optional[str] = None
    # Number of port to expose on the pod's IP address. This must be a valid port number, 0 < x < 65536.
    container_port: int = Field(..., alias="containerPort")
    host_ip: Optional[str] = Field(None, alias="hostIP")
    # Number of port to expose on the host.
    # If specified, this must be a valid port number, 0 < x < 65536.
    # If HostNetwork is specified, this must match ContainerPort.
    # Most containers do not need this.
    host_port: Optional[int] = Field(None, alias="hostPort")
    protocol: Optional[Protocol] = None

    @field_serializer("protocol")
    def get_protocol_value(self, v) -> Optional[str]:
        return v.value if v else None

    def get_k8s_object(self) -> V1ContainerPort:
        _v1_container_port = V1ContainerPort(
            container_port=self.container_port,
            name=self.name,
            protocol=self.protocol.value if self.protocol else None,
            host_ip=self.host_ip,
            host_port=self.host_port,
        )
        return _v1_container_port


class VolumeMount(K8sObject):
    """
    VolumeMount describes a mounting of a Volume within a container.

    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#volumemount-v1-core
    """

    resource_type: str = "VolumeMount"

    # Path within the container at which the volume should be mounted. Must not contain ':'
    mount_path: str = Field(..., alias="mountPath")
    # mountPropagation determines how mounts are propagated from the host to container and the other way around.
    # When not set, MountPropagationNone is used. This field is beta in 1.10.
    mount_propagation: Optional[str] = Field(None, alias="mountPropagation")
    # This must match the Name of a Volume.
    name: str
    # Mounted read-only if true, read-write otherwise (false or unspecified). Defaults to false.
    read_only: Optional[bool] = Field(None, alias="readOnly")
    # Path within the volume from which the container's volume should be mounted. Defaults to "" (volume's root).
    sub_path: Optional[str] = Field(None, alias="subPath")
    # Expanded path within the volume from which the container's volume should be mounted.
    # Behaves similarly to SubPath but environment variable references $(VAR_NAME) are expanded using the
    # container's environment.
    # Defaults to "" (volume's root). SubPathExpr and SubPath are mutually exclusive.
    sub_path_expr: Optional[str] = Field(None, alias="subPathExpr")

    def get_k8s_object(self) -> V1VolumeMount:
        _v1_volume_mount = V1VolumeMount(
            mount_path=self.mount_path,
            mount_propagation=self.mount_propagation,
            name=self.name,
            read_only=self.read_only,
            sub_path=self.sub_path,
            sub_path_expr=self.sub_path_expr,
        )
        return _v1_volume_mount


class Container(K8sObject):
    """
    Reference:
    - https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.23/#container-v1-core
    """

    resource_type: str = "Container"

    # Arguments to the entrypoint. The docker image's CMD is used if this is not provided.
    args: Optional[List[str]] = None
    # Entrypoint array. Not executed within a shell. The docker image's ENTRYPOINT is used if this is not provided.
    command: Optional[List[str]] = None
    env: Optional[List[EnvVar]] = None
    env_from: Optional[List[EnvFromSource]] = Field(None, alias="envFrom")
    # Docker image name.
    image: str
    # Image pull policy. One of Always, Never, IfNotPresent.
    # Defaults to Always if :latest tag is specified, or IfNotPresent otherwise.
    image_pull_policy: Optional[ImagePullPolicy] = Field(None, alias="imagePullPolicy")
    # Name of the container specified as a DNS_LABEL.
    # Each container in a pod must have a unique name (DNS_LABEL).
    name: str
    # List of ports to expose from the container.
    # Exposing a port here gives the system additional information about the network connections a container uses,
    # but is primarily informational.
    # Not specifying a port here DOES NOT prevent that port from being exposed.
    ports: Optional[List[ContainerPort]] = None
    # TODO: add Probe object
    # Periodic probe of container service readiness.
    # Container will be removed from service endpoints if the probe fails. Cannot be updated.
    readiness_probe: Optional[Probe] = Field(None, alias="readinessProbe")
    # Compute Resources required by this container. Cannot be updated.
    resources: Optional[ResourceRequirements] = None
    volume_mounts: Optional[List[VolumeMount]] = Field(None, alias="volumeMounts")
    working_dir: Optional[str] = Field(None, alias="workingDir")

    @field_serializer("image_pull_policy")
    def get_image_pull_policy_value(self, v) -> Optional[str]:
        return v.value if v else None

    def get_k8s_object(self) -> V1Container:
        # Return a V1Container object
        # https://github.com/kubernetes-client/python/blob/master/kubernetes/client/models/v1_container.py
        _ports: Optional[List[V1ContainerPort]] = None
        if self.ports:
            _ports = [_cp.get_k8s_object() for _cp in self.ports]

        _env: Optional[List[V1EnvVar]] = None
        if self.env:
            _env = [_e.get_k8s_object() for _e in self.env]

        _env_from: Optional[List[V1EnvFromSource]] = None
        if self.env_from:
            _env_from = [_ef.get_k8s_object() for _ef in self.env_from]

        _volume_mounts: Optional[List[V1VolumeMount]] = None
        if self.volume_mounts:
            _volume_mounts = [_vm.get_k8s_object() for _vm in self.volume_mounts]

        _v1_container = V1Container(
            args=self.args,
            command=self.command,
            env=_env,
            env_from=_env_from,
            image=self.image,
            image_pull_policy=self.image_pull_policy.value if self.image_pull_policy else None,
            name=self.name,
            ports=_ports,
            readiness_probe=self.readiness_probe.get_k8s_object() if self.readiness_probe else None,
            resources=self.resources.get_k8s_object() if self.resources else None,
            volume_mounts=_volume_mounts,
        )
        return _v1_container

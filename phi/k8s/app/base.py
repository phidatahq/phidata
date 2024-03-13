from collections import OrderedDict
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, Union, List, TYPE_CHECKING
from typing_extensions import Literal

from pydantic import field_validator, Field, model_validator
from pydantic_core.core_schema import FieldValidationInfo

from phi.app.base import AppBase
from phi.app.context import ContainerContext
from phi.k8s.app.context import K8sBuildContext
from phi.k8s.enums.restart_policy import RestartPolicy
from phi.k8s.enums.image_pull_policy import ImagePullPolicy
from phi.k8s.enums.service_type import ServiceType
from phi.utils.log import logger

if TYPE_CHECKING:
    from phi.k8s.resource.base import K8sResource


class K8sWorkspaceVolumeType(str, Enum):
    HostPath = "HostPath"
    EmptyDir = "EmptyDir"


class AppVolumeType(str, Enum):
    HostPath = "HostPath"
    EmptyDir = "EmptyDir"
    AwsEbs = "AwsEbs"
    AwsEfs = "AwsEfs"
    PersistentVolume = "PersistentVolume"


class LoadBalancerProvider(str, Enum):
    AWS = "AWS"


class K8sApp(AppBase):
    # -*- Workspace Configuration
    # Path to the workspace directory inside the container
    # NOTE: if workspace_parent_dir_container_path is provided
    #   workspace_dir_container_path is ignored and
    #   derived using {workspace_parent_dir_container_path}/{workspace_name}
    workspace_dir_container_path: str = "/usr/local/app"
    # Path to the parent directory of the workspace inside the container
    # When using git-sync, the git repo is cloned inside this directory
    #   i.e. this is the parent directory of the workspace
    workspace_parent_dir_container_path: Optional[str] = None

    # Mount the workspace directory inside the container
    mount_workspace: bool = False
    # -*- If workspace_volume_type is None or K8sWorkspaceVolumeType.EmptyDir
    #   Create an empty volume with the name workspace_volume_name
    #   which is mounted to workspace_parent_dir_container_path
    # -*- If workspace_volume_type is K8sWorkspaceVolumeType.HostPath
    #   Mount the workspace_root to workspace_dir_container_path
    #   i.e. {workspace_parent_dir_container_path}/{workspace_name}
    workspace_volume_type: Optional[K8sWorkspaceVolumeType] = None
    workspace_volume_name: Optional[str] = None
    # Load the workspace from git using a git-sync sidecar
    enable_gitsync: bool = False
    # Use an init-container to create an initial copy of the workspace
    create_gitsync_init_container: bool = True
    gitsync_image_name: str = "registry.k8s.io/git-sync/git-sync"
    gitsync_image_tag: str = "v4.0.0"
    # Repository to sync
    gitsync_repo: Optional[str] = None
    # Branch to sync
    gitsync_ref: Optional[str] = None
    gitsync_period: Optional[str] = None
    # Add configuration using env vars to the gitsync container
    gitsync_env: Optional[Dict[str, str]] = None

    # -*- App Volume
    # Create a volume for container storage
    # Used for mounting app data like database, notebooks, models, etc.
    create_volume: bool = False
    volume_name: Optional[str] = None
    volume_type: AppVolumeType = AppVolumeType.EmptyDir
    # Path to mount the app volume inside the container
    volume_container_path: str = "/mnt/app"
    # -*- If volume_type is HostPath
    volume_host_path: Optional[str] = None
    # -*- If volume_type is AwsEbs
    # Provide Ebs Volume-id manually
    ebs_volume_id: Optional[str] = None
    # OR derive the volume_id, region, and az from an EbsVolume resource
    ebs_volume: Optional[Any] = None
    ebs_volume_region: Optional[str] = None
    ebs_volume_az: Optional[str] = None
    # Add NodeSelectors to Pods, so they are scheduled in the same region and zone as the ebs_volume
    schedule_pods_in_ebs_topology: bool = True
    # -*- If volume_type=AppVolumeType.AwsEfs
    # Provide Efs Volume-id manually
    efs_volume_id: Optional[str] = None
    # OR derive the volume_id from an EfsVolume resource
    efs_volume: Optional[Any] = None
    # -*- If volume_type=AppVolumeType.PersistentVolume
    # AccessModes is a list of ways the volume can be mounted.
    # More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#access-modes
    # Type: phidata.infra.k8s.enums.pv.PVAccessMode
    pv_access_modes: Optional[List[Any]] = None
    pv_requests_storage: Optional[str] = None
    # A list of mount options, e.g. ["ro", "soft"]. Not validated - mount will simply fail if one is invalid.
    # More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes/#mount-options
    pv_mount_options: Optional[List[str]] = None
    # What happens to a persistent volume when released from its claim.
    #   The default policy is Retain.
    # Literal["Delete", "Recycle", "Retain"]
    pv_reclaim_policy: Optional[str] = None
    pv_storage_class: str = ""
    pv_labels: Optional[Dict[str, str]] = None

    # -*- Container Configuration
    container_name: Optional[str] = None
    container_labels: Optional[Dict[str, str]] = None

    # -*- Pod Configuration
    pod_name: Optional[str] = None
    pod_annotations: Optional[Dict[str, str]] = None
    pod_node_selector: Optional[Dict[str, str]] = None

    # -*- Secret Configuration
    secret_name: Optional[str] = None

    # -*- Configmap Configuration
    configmap_name: Optional[str] = None

    # -*- Deployment Configuration
    replicas: int = 1
    deploy_name: Optional[str] = None
    image_pull_policy: Optional[ImagePullPolicy] = None
    restart_policy: Optional[RestartPolicy] = None
    deploy_labels: Optional[Dict[str, Any]] = None
    termination_grace_period_seconds: Optional[int] = None
    # Key to spread the pods across a topology
    topology_spread_key: str = "kubernetes.io/hostname"
    # The degree to which pods may be unevenly distributed
    topology_spread_max_skew: int = 2
    # How to deal with a pod if it doesn't satisfy the spread constraint.
    topology_spread_when_unsatisfiable: Literal["DoNotSchedule", "ScheduleAnyway"] = "ScheduleAnyway"

    # -*- Service Configuration
    create_service: bool = False
    service_name: Optional[str] = None
    service_type: Optional[ServiceType] = None
    # -*- Enable HTTPS on the Service if service_type = ServiceType.LOAD_BALANCER
    # Must provide an ACM Certificate ARN or ACM Certificate Summary File to work
    enable_https: bool = False
    # The port exposed by the service
    # Preferred over port_number if both are set
    service_port: Optional[int] = Field(None, validate_default=True)
    # The node_port exposed by the service if service_type = ServiceType.NODE_PORT
    service_node_port: Optional[int] = None
    # The target_port is the port to access on the pods targeted by the service.
    # It can be the port number or port name on the pod.
    service_target_port: Optional[Union[str, int]] = None
    # Extra ports exposed by the service. Type: List[CreatePort]
    service_ports: Optional[List[Any]] = None
    # Labels to add to the service
    service_labels: Optional[Dict[str, Any]] = None
    # Annotations to add to the service
    service_annotations: Optional[Dict[str, str]] = None

    # -*- LoadBalancer configuration
    health_check_node_port: Optional[int] = None
    internal_traffic_policy: Optional[str] = None
    load_balancer_ip: Optional[str] = None
    # https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.5/guide/service/nlb/
    load_balancer_class: Optional[str] = None
    # Limit the IPs that can access this endpoint
    # You can provide the load_balancer_source_ranges as a list here
    # or as LOAD_BALANCER_SOURCE_RANGES in the secrets_file
    # Using the secrets_file is recommended
    load_balancer_source_ranges: Optional[List[str]] = None
    allocate_load_balancer_node_ports: Optional[bool] = None

    # -*- AWS LoadBalancer configuration
    # If ServiceType == ServiceType.LoadBalancer, the load balancer is created using the AWS LoadBalancer Controller
    # and the following configuration are added as annotations to the service
    use_nlb: bool = True
    # Specifies the target type to configure for NLB. You can choose between instance and ip.
    # `instance` mode will route traffic to all EC2 instances within cluster on the NodePort opened for your service.
    #       service must be of type NodePort or LoadBalancer for instance targets
    #       for k8s 1.22 and later if spec.allocateLoadBalancerNodePorts is set to false,
    #       NodePort must be allocated manually
    # `ip` mode will route traffic directly to the pod IP.
    #       network plugin must use native AWS VPC networking configuration for pod IP,
    #       for example Amazon VPC CNI plugin.
    nlb_target_type: Literal["instance", "ip"] = "ip"
    # If None, default is "internet-facing"
    load_balancer_scheme: Literal["internal", "internet-facing"] = "internet-facing"
    # Write Access Logs to s3
    write_access_logs_to_s3: bool = False
    # The name of the aws S3 bucket where the access logs are stored
    access_logs_s3_bucket: Optional[str] = None
    # The logical hierarchy you created for your aws S3 bucket, for example `my-bucket-prefix/prod`
    access_logs_s3_bucket_prefix: Optional[str] = None
    acm_certificate_arn: Optional[str] = None
    acm_certificate_summary_file: Optional[Path] = None
    # Enable proxy protocol for NLB
    enable_load_balancer_proxy_protocol: bool = True
    # Enable cross-zone load balancing
    enable_cross_zone_load_balancing: bool = True
    # Manually specify the subnets to use for the load balancer
    load_balancer_subnets: Optional[List[str]] = None

    # -*- Ingress Configuration
    create_ingress: bool = False
    ingress_name: Optional[str] = None
    ingress_class_name: Literal["alb", "nlb"] = "alb"
    ingress_annotations: Optional[Dict[str, str]] = None

    # -*- Namespace Configuration
    create_namespace: bool = False
    # Create a Namespace with name ns_name & default values
    ns_name: Optional[str] = None
    # or Provide the full Namespace definition
    # Type: CreateNamespace
    namespace: Optional[Any] = None

    # -*- RBAC Configuration
    # If create_rbac = True, create a ServiceAccount, ClusterRole, and ClusterRoleBinding
    create_rbac: bool = False
    # -*- ServiceAccount Configuration
    create_service_account: Optional[bool] = Field(None, validate_default=True)
    # Create a ServiceAccount with name sa_name & default values
    sa_name: Optional[str] = None
    # or Provide the full ServiceAccount definition
    # Type: CreateServiceAccount
    service_account: Optional[Any] = None
    # -*- ClusterRole Configuration
    create_cluster_role: Optional[bool] = Field(None, validate_default=True)
    # Create a ClusterRole with name cr_name & default values
    cr_name: Optional[str] = None
    # or Provide the full ClusterRole definition
    # Type: CreateClusterRole
    cluster_role: Optional[Any] = None
    # -*- ClusterRoleBinding Configuration
    create_cluster_role_binding: Optional[bool] = Field(None, validate_default=True)
    # Create a ClusterRoleBinding with name crb_name & default values
    crb_name: Optional[str] = None
    # or Provide the full ClusterRoleBinding definition
    # Type: CreateClusterRoleBinding
    cluster_role_binding: Optional[Any] = None

    # -*- Add additional Kubernetes resources to the App
    # Type: CreateSecret
    add_secrets: Optional[List[Any]] = None
    # Type: CreateConfigMap
    add_configmaps: Optional[List[Any]] = None
    # Type: CreateService
    add_services: Optional[List[Any]] = None
    # Type: CreateDeployment
    add_deployments: Optional[List[Any]] = None
    # Type: CreateContainer
    add_containers: Optional[List[Any]] = None
    # Type: CreateContainer
    add_init_containers: Optional[List[Any]] = None
    # Type: CreatePort
    add_ports: Optional[List[Any]] = None
    # Type: CreateVolume
    add_volumes: Optional[List[Any]] = None
    # Type: K8sResource or CreateK8sResource
    add_resources: Optional[List[Any]] = None

    # -*- Add additional YAML resources to the App
    # Type: YamlResource
    yaml_resources: Optional[List[Any]] = None

    @field_validator("service_port", mode="before")
    def set_service_port(cls, v, info: FieldValidationInfo):
        port_number = info.data.get("port_number")
        service_type: Optional[ServiceType] = info.data.get("service_type")
        enable_https = info.data.get("enable_https")
        if v is None:
            if service_type == ServiceType.LOAD_BALANCER:
                if enable_https:
                    v = 443
                else:
                    v = 80
            elif port_number is not None:
                v = port_number
        return v

    @field_validator("create_service_account", mode="before")
    def set_create_service_account(cls, v, info: FieldValidationInfo):
        create_rbac = info.data.get("create_rbac")
        if v is None and create_rbac:
            v = create_rbac
        return v

    @field_validator("create_cluster_role", mode="before")
    def set_create_cluster_role(cls, v, info: FieldValidationInfo):
        create_rbac = info.data.get("create_rbac")
        if v is None and create_rbac:
            v = create_rbac
        return v

    @field_validator("create_cluster_role_binding", mode="before")
    def set_create_cluster_role_binding(cls, v, info: FieldValidationInfo):
        create_rbac = info.data.get("create_rbac")
        if v is None and create_rbac:
            v = create_rbac
        return v

    @model_validator(mode="after")
    def validate_model(self) -> "K8sApp":
        if self.enable_https:
            if self.acm_certificate_arn is None and self.acm_certificate_summary_file is None:
                raise ValueError(
                    "Must provide an ACM Certificate ARN or ACM Certificate Summary File if enable_https=True"
                )
        return self

    def get_cr_name(self) -> str:
        from phi.utils.defaults import get_default_cr_name

        return self.cr_name or get_default_cr_name(self.name)

    def get_crb_name(self) -> str:
        from phi.utils.defaults import get_default_crb_name

        return self.crb_name or get_default_crb_name(self.name)

    def get_configmap_name(self) -> str:
        from phi.utils.defaults import get_default_configmap_name

        return self.configmap_name or get_default_configmap_name(self.name)

    def get_secret_name(self) -> str:
        from phi.utils.defaults import get_default_secret_name

        return self.secret_name or get_default_secret_name(self.name)

    def get_container_name(self) -> str:
        from phi.utils.defaults import get_default_container_name

        return self.container_name or get_default_container_name(self.name)

    def get_deploy_name(self) -> str:
        from phi.utils.defaults import get_default_deploy_name

        return self.deploy_name or get_default_deploy_name(self.name)

    def get_pod_name(self) -> str:
        from phi.utils.defaults import get_default_pod_name

        return self.pod_name or get_default_pod_name(self.name)

    def get_service_name(self) -> str:
        from phi.utils.defaults import get_default_service_name

        return self.service_name or get_default_service_name(self.name)

    def get_service_port(self) -> Optional[int]:
        return self.service_port

    def get_service_annotations(self) -> Optional[Dict[str, str]]:
        service_annotations = self.service_annotations

        # Add annotations to create an AWS LoadBalancer
        # https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.5/guide/service/nlb/
        if self.service_type == ServiceType.LOAD_BALANCER:
            if service_annotations is None:
                service_annotations = OrderedDict()
            if self.use_nlb:
                service_annotations["service.beta.kubernetes.io/aws-load-balancer-type"] = "nlb"
                service_annotations["service.beta.kubernetes.io/aws-load-balancer-nlb-target-type"] = (
                    self.nlb_target_type
                )

            if self.load_balancer_scheme is not None:
                service_annotations["service.beta.kubernetes.io/aws-load-balancer-scheme"] = self.load_balancer_scheme
                if self.load_balancer_scheme == "internal":
                    service_annotations["service.beta.kubernetes.io/aws-load-balancer-internal"] = "true"

            # https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.4/guide/service/annotations/#load-balancer-attributes
            # Deprecated docs: # https://kubernetes.io/docs/concepts/services-networking/service/#elb-access-logs-on-aws
            if self.write_access_logs_to_s3:
                service_annotations["service.beta.kubernetes.io/aws-load-balancer-access-log-enabled"] = "true"
                lb_attributes = "access_logs.s3.enabled=true"
                if self.access_logs_s3_bucket is not None:
                    service_annotations["service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-name"] = (
                        self.access_logs_s3_bucket
                    )
                    lb_attributes += f",access_logs.s3.bucket={self.access_logs_s3_bucket}"
                if self.access_logs_s3_bucket_prefix is not None:
                    service_annotations["service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-prefix"] = (
                        self.access_logs_s3_bucket_prefix
                    )
                    lb_attributes += f",access_logs.s3.prefix={self.access_logs_s3_bucket_prefix}"
                service_annotations["service.beta.kubernetes.io/aws-load-balancer-attributes"] = lb_attributes

            # https://kubernetes.io/docs/concepts/services-networking/service/#ssl-support-on-aws
            if self.enable_https:
                service_annotations["service.beta.kubernetes.io/aws-load-balancer-ssl-ports"] = str(
                    self.get_service_port()
                )

                # https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.4/guide/service/annotations/#ssl-cert
                if self.acm_certificate_arn is not None:
                    service_annotations["service.beta.kubernetes.io/aws-load-balancer-ssl-cert"] = (
                        self.acm_certificate_arn
                    )
                # if acm_certificate_summary_file is provided, use that
                if self.acm_certificate_summary_file is not None and isinstance(
                    self.acm_certificate_summary_file, Path
                ):
                    if self.acm_certificate_summary_file.exists() and self.acm_certificate_summary_file.is_file():
                        from phi.aws.resource.acm.certificate import CertificateSummary

                        file_contents = self.acm_certificate_summary_file.read_text()
                        cert_summary = CertificateSummary.model_validate(file_contents)
                        certificate_arn = cert_summary.CertificateArn
                        logger.debug(f"CertificateArn: {certificate_arn}")
                        service_annotations["service.beta.kubernetes.io/aws-load-balancer-ssl-cert"] = certificate_arn
                    else:
                        logger.warning(f"Does not exist: {self.acm_certificate_summary_file}")

            # Enable proxy protocol for NLB
            if self.enable_load_balancer_proxy_protocol:
                service_annotations["service.beta.kubernetes.io/aws-load-balancer-proxy-protocol"] = "*"

            # Enable cross-zone load balancing
            if self.enable_cross_zone_load_balancing:
                service_annotations[
                    "service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled"
                ] = "true"

            # Add subnets to NLB
            if self.load_balancer_subnets is not None and isinstance(self.load_balancer_subnets, list):
                service_annotations["service.beta.kubernetes.io/aws-load-balancer-subnets"] = ", ".join(
                    self.load_balancer_subnets
                )

        return service_annotations

    def get_ingress_name(self) -> str:
        from phi.utils.defaults import get_default_ingress_name

        return self.ingress_name or get_default_ingress_name(self.name)

    def get_ingress_annotations(self) -> Optional[Dict[str, str]]:
        ingress_annotations = {"alb.ingress.kubernetes.io/load-balancer-name": self.get_ingress_name()}

        if self.load_balancer_scheme == "internal":
            ingress_annotations["alb.ingress.kubernetes.io/scheme"] = "internal"
        else:
            ingress_annotations["alb.ingress.kubernetes.io/scheme"] = "internet-facing"

        if self.load_balancer_subnets is not None and isinstance(self.load_balancer_subnets, list):
            ingress_annotations["alb.ingress.kubernetes.io/subnets"] = ", ".join(self.load_balancer_subnets)

        if self.ingress_annotations is not None:
            ingress_annotations.update(self.ingress_annotations)

        return ingress_annotations

    def get_ingress_rules(self) -> List[Any]:
        from kubernetes.client.models.v1_ingress_rule import V1IngressRule
        from kubernetes.client.models.v1_ingress_backend import V1IngressBackend
        from kubernetes.client.models.v1_ingress_service_backend import V1IngressServiceBackend
        from kubernetes.client.models.v1_http_ingress_path import V1HTTPIngressPath
        from kubernetes.client.models.v1_http_ingress_rule_value import V1HTTPIngressRuleValue
        from kubernetes.client.models.v1_service_port import V1ServicePort

        return [
            V1IngressRule(
                http=V1HTTPIngressRuleValue(
                    paths=[
                        V1HTTPIngressPath(
                            path="/",
                            path_type="Prefix",
                            backend=V1IngressBackend(
                                service=V1IngressServiceBackend(
                                    name=self.get_service_name(),
                                    port=V1ServicePort(
                                        name=self.container_port_name,
                                        port=self.get_service_port(),
                                    ),
                                )
                            ),
                        ),
                    ]
                ),
            )
        ]

    def get_load_balancer_source_ranges(self) -> Optional[List[str]]:
        if self.load_balancer_source_ranges is not None:
            return self.load_balancer_source_ranges

        load_balancer_source_ranges = self.get_secret_from_file("LOAD_BALANCER_SOURCE_RANGES")
        if isinstance(load_balancer_source_ranges, str):
            return [load_balancer_source_ranges]
        return load_balancer_source_ranges

    def get_cr_policy_rules(self) -> List[Any]:
        from phi.k8s.create.rbac_authorization_k8s_io.v1.cluster_role import (
            PolicyRule,
        )

        return [
            PolicyRule(
                api_groups=[""],
                resources=["pods", "secrets", "configmaps"],
                verbs=["get", "list", "watch", "create", "update", "patch", "delete"],
            ),
            PolicyRule(
                api_groups=[""],
                resources=["pods/logs"],
                verbs=["get", "list", "watch"],
            ),
            PolicyRule(
                api_groups=[""],
                resources=["pods/exec"],
                verbs=["get", "create", "watch", "delete"],
            ),
        ]

    def get_container_context(self) -> Optional[ContainerContext]:
        logger.debug("Building ContainerContext")

        if self.container_context is not None:
            return self.container_context

        workspace_name = self.workspace_name
        if workspace_name is None:
            raise Exception("Could not determine workspace_name")

        workspace_root_in_container: str = self.workspace_dir_container_path
        # if workspace_parent_dir_container_path is provided
        # derive workspace_root_in_container from workspace_parent_dir_container_path
        workspace_parent_in_container: Optional[str] = self.workspace_parent_dir_container_path
        if workspace_parent_in_container is not None:
            workspace_root_in_container = f"{self.workspace_parent_dir_container_path}/{workspace_name}"

        if workspace_root_in_container is None:
            raise Exception("Could not determine workspace_root in container")

        # if workspace_parent_in_container is not provided
        # derive workspace_parent_in_container from workspace_root_in_container
        if workspace_parent_in_container is None:
            workspace_parent_paths = workspace_root_in_container.split("/")[0:-1]
            workspace_parent_in_container = "/".join(workspace_parent_paths)

        self.container_context = ContainerContext(
            workspace_name=workspace_name,
            workspace_root=workspace_root_in_container,
            workspace_parent=workspace_parent_in_container,
        )

        if self.workspace_settings is not None and self.workspace_settings.scripts_dir is not None:
            self.container_context.scripts_dir = f"{workspace_root_in_container}/{self.workspace_settings.scripts_dir}"

        if self.workspace_settings is not None and self.workspace_settings.storage_dir is not None:
            self.container_context.storage_dir = f"{workspace_root_in_container}/{self.workspace_settings.storage_dir}"

        if self.workspace_settings is not None and self.workspace_settings.workflows_dir is not None:
            self.container_context.workflows_dir = (
                f"{workspace_root_in_container}/{self.workspace_settings.workflows_dir}"
            )

        if self.workspace_settings is not None and self.workspace_settings.workspace_dir is not None:
            self.container_context.workspace_dir = (
                f"{workspace_root_in_container}/{self.workspace_settings.workspace_dir}"
            )

        if self.workspace_settings is not None and self.workspace_settings.ws_schema is not None:
            self.container_context.workspace_schema = self.workspace_settings.ws_schema

        if self.requirements_file is not None:
            self.container_context.requirements_file = f"{workspace_root_in_container}/{self.requirements_file}"

        return self.container_context

    def get_container_env(self, container_context: ContainerContext) -> Dict[str, str]:
        from phi.constants import (
            PHI_RUNTIME_ENV_VAR,
            PYTHONPATH_ENV_VAR,
            REQUIREMENTS_FILE_PATH_ENV_VAR,
            SCRIPTS_DIR_ENV_VAR,
            STORAGE_DIR_ENV_VAR,
            WORKFLOWS_DIR_ENV_VAR,
            WORKSPACE_DIR_ENV_VAR,
            WORKSPACE_HASH_ENV_VAR,
            WORKSPACE_ID_ENV_VAR,
            WORKSPACE_ROOT_ENV_VAR,
        )

        # Container Environment
        container_env: Dict[str, str] = self.container_env or {}
        container_env.update(
            {
                "INSTALL_REQUIREMENTS": str(self.install_requirements),
                "MOUNT_WORKSPACE": str(self.mount_workspace),
                "PRINT_ENV_ON_LOAD": str(self.print_env_on_load),
                PHI_RUNTIME_ENV_VAR: "kubernetes",
                REQUIREMENTS_FILE_PATH_ENV_VAR: container_context.requirements_file or "",
                SCRIPTS_DIR_ENV_VAR: container_context.scripts_dir or "",
                STORAGE_DIR_ENV_VAR: container_context.storage_dir or "",
                WORKFLOWS_DIR_ENV_VAR: container_context.workflows_dir or "",
                WORKSPACE_DIR_ENV_VAR: container_context.workspace_dir or "",
                WORKSPACE_ROOT_ENV_VAR: container_context.workspace_root or "",
            }
        )

        try:
            if container_context.workspace_schema is not None:
                if container_context.workspace_schema.id_workspace is not None:
                    container_env[WORKSPACE_ID_ENV_VAR] = str(container_context.workspace_schema.id_workspace) or ""
                if container_context.workspace_schema.ws_hash is not None:
                    container_env[WORKSPACE_HASH_ENV_VAR] = container_context.workspace_schema.ws_hash
        except Exception:
            pass

        if self.set_python_path:
            python_path = self.python_path
            if python_path is None:
                python_path = container_context.workspace_root
                if self.add_python_paths is not None:
                    python_path = "{}:{}".format(python_path, ":".join(self.add_python_paths))
            if python_path is not None:
                container_env[PYTHONPATH_ENV_VAR] = python_path

        # Set aws region and profile
        self.set_aws_env_vars(env_dict=container_env)

        # Update the container env using env_file
        env_data_from_file = self.get_env_file_data()
        if env_data_from_file is not None:
            container_env.update({k: str(v) for k, v in env_data_from_file.items() if v is not None})

        # Update the container env with user provided env_vars
        # this overwrites any existing variables with the same key
        if self.env_vars is not None and isinstance(self.env_vars, dict):
            container_env.update({k: str(v) for k, v in self.env_vars.items() if v is not None})

        # logger.debug("Container Environment: {}".format(container_env))
        return container_env

    def get_container_args(self) -> Optional[List[str]]:
        if isinstance(self.command, str):
            return self.command.strip().split(" ")
        return self.command

    def get_container_labels(self, common_labels: Optional[Dict[str, str]]) -> Dict[str, str]:
        labels: Dict[str, str] = common_labels or {}
        if self.container_labels is not None and isinstance(self.container_labels, dict):
            labels.update(self.container_labels)
        return labels

    def get_deployment_labels(self, common_labels: Optional[Dict[str, str]]) -> Dict[str, str]:
        labels: Dict[str, str] = common_labels or {}
        if self.container_labels is not None and isinstance(self.container_labels, dict):
            labels.update(self.container_labels)
        return labels

    def get_service_labels(self, common_labels: Optional[Dict[str, str]]) -> Dict[str, str]:
        labels: Dict[str, str] = common_labels or {}
        if self.container_labels is not None and isinstance(self.container_labels, dict):
            labels.update(self.container_labels)
        return labels

    def get_secrets(self) -> List[Any]:
        return self.add_secrets or []

    def get_configmaps(self) -> List[Any]:
        return self.add_configmaps or []

    def get_services(self) -> List[Any]:
        return self.add_services or []

    def get_deployments(self) -> List[Any]:
        return self.add_deployments or []

    def get_containers(self) -> List[Any]:
        return self.add_containers or []

    def get_volumes(self) -> List[Any]:
        return self.add_volumes or []

    def get_ports(self) -> List[Any]:
        return self.add_ports or []

    def get_init_containers(self) -> List[Any]:
        return self.add_init_containers or []

    def add_app_resources(self, namespace: str, service_account_name: Optional[str]) -> List[Any]:
        return self.add_resources or []

    def build_resources(self, build_context: K8sBuildContext) -> List["K8sResource"]:
        from phi.k8s.create.apps.v1.deployment import CreateDeployment
        from phi.k8s.create.base import CreateK8sResource
        from phi.k8s.create.common.port import CreatePort
        from phi.k8s.create.core.v1.config_map import CreateConfigMap
        from phi.k8s.create.core.v1.container import CreateContainer
        from phi.k8s.create.core.v1.namespace import CreateNamespace
        from phi.k8s.create.core.v1.secret import CreateSecret
        from phi.k8s.create.core.v1.service import CreateService
        from phi.k8s.create.core.v1.service_account import CreateServiceAccount
        from phi.k8s.create.core.v1.volume import (
            CreateVolume,
            HostPathVolumeSource,
            AwsElasticBlockStoreVolumeSource,
            VolumeType,
        )
        from phi.k8s.create.networking_k8s_io.v1.ingress import CreateIngress
        from phi.k8s.create.rbac_authorization_k8s_io.v1.cluste_role_binding import CreateClusterRoleBinding
        from phi.k8s.create.rbac_authorization_k8s_io.v1.cluster_role import CreateClusterRole
        from phi.k8s.resource.base import K8sResource
        from phi.k8s.resource.yaml import YamlResource
        from phi.utils.defaults import get_default_volume_name, get_default_sa_name

        logger.debug(f"------------ Building {self.get_app_name()} ------------")
        # -*- Initialize K8s resources
        ns: Optional[CreateNamespace] = self.namespace
        sa: Optional[CreateServiceAccount] = self.service_account
        cr: Optional[CreateClusterRole] = self.cluster_role
        crb: Optional[CreateClusterRoleBinding] = self.cluster_role_binding
        secrets: List[CreateSecret] = self.get_secrets()
        config_maps: List[CreateConfigMap] = self.get_configmaps()
        services: List[CreateService] = self.get_services()
        deployments: List[CreateDeployment] = self.get_deployments()
        containers: List[CreateContainer] = self.get_containers()
        init_containers: List[CreateContainer] = self.get_init_containers()
        ports: List[CreatePort] = self.get_ports()
        volumes: List[CreateVolume] = self.get_volumes()

        # -*- Namespace name for this App
        # Use the Namespace name provided by the App or the default from the build_context
        # If self.create_rbac is True, the Namespace is created by the App if self.namespace is None
        ns_name: str = self.ns_name or build_context.namespace

        # -*- Service Account name for this App
        # Use the Service Account provided by the App or the default from the build_context
        sa_name: Optional[str] = self.sa_name or build_context.service_account_name

        # Use the labels from the build_context as common labels for all resources
        common_labels: Optional[Dict[str, str]] = build_context.labels

        # -*- Create Namespace
        if self.create_namespace:
            if ns is None:
                ns = CreateNamespace(
                    ns=ns_name,
                    app_name=self.get_app_name(),
                    labels=common_labels,
                )
            ns_name = ns.ns

        # -*- Create Service Account
        if self.create_service_account:
            if sa is None:
                sa = CreateServiceAccount(
                    sa_name=sa_name or get_default_sa_name(self.get_app_name()),
                    app_name=self.get_app_name(),
                    namespace=ns_name,
                )
            sa_name = sa.sa_name

        # -*- Create Cluster Role
        if self.create_cluster_role:
            if cr is None:
                cr = CreateClusterRole(
                    cr_name=self.get_cr_name(),
                    rules=self.get_cr_policy_rules(),
                    app_name=self.get_app_name(),
                    labels=common_labels,
                )

        # -*- Create ClusterRoleBinding
        if self.create_cluster_role_binding:
            if crb is None:
                if cr is None:
                    logger.error(
                        "ClusterRoleBinding requires a ClusterRole. "
                        "Please set create_cluster_role = True or provide a ClusterRole"
                    )
                    return []
                if sa is None:
                    logger.error(
                        "ClusterRoleBinding requires a ServiceAccount. "
                        "Please set create_service_account = True or provide a ServiceAccount"
                    )
                    return []
                crb = CreateClusterRoleBinding(
                    crb_name=self.get_crb_name(),
                    cr_name=cr.cr_name,
                    service_account_name=sa.sa_name,
                    app_name=self.get_app_name(),
                    namespace=ns_name,
                    labels=common_labels,
                )

        # -*- Get Container Context
        container_context: Optional[ContainerContext] = self.get_container_context()
        if container_context is None:
            raise Exception("Could not build ContainerContext")
        logger.debug(f"ContainerContext: {container_context.model_dump_json(indent=2)}")

        # -*- Get Container Environment
        container_env: Dict[str, str] = self.get_container_env(container_context=container_context)

        # -*- Get ConfigMaps
        container_env_cm = CreateConfigMap(
            cm_name=self.get_configmap_name(),
            app_name=self.get_app_name(),
            namespace=ns_name,
            data=container_env,
            labels=common_labels,
        )
        config_maps.append(container_env_cm)

        # -*- Get Secrets
        secret_data_from_file = self.get_secret_file_data()
        if secret_data_from_file is not None:
            container_env_secret = CreateSecret(
                secret_name=self.get_secret_name(),
                app_name=self.get_app_name(),
                string_data=secret_data_from_file,
                namespace=ns_name,
                labels=common_labels,
            )
            secrets.append(container_env_secret)

        # -*- Get Container Volumes
        if self.mount_workspace:
            # Build workspace_volume_name
            workspace_volume_name = self.workspace_volume_name
            if workspace_volume_name is None:
                workspace_volume_name = get_default_volume_name(
                    f"{self.get_app_name()}-{container_context.workspace_name}-ws"
                )

            # If workspace_volume_type is None or EmptyDir
            if self.workspace_volume_type is None or self.workspace_volume_type == K8sWorkspaceVolumeType.EmptyDir:
                logger.debug("Creating EmptyDir")
                logger.debug(f"    at: {container_context.workspace_parent}")
                workspace_volume = CreateVolume(
                    volume_name=workspace_volume_name,
                    app_name=self.get_app_name(),
                    mount_path=container_context.workspace_parent,
                    volume_type=VolumeType.EMPTY_DIR,
                )
                volumes.append(workspace_volume)

                if self.enable_gitsync:
                    if self.gitsync_repo is not None:
                        git_sync_env: Dict[str, str] = {
                            "GITSYNC_REPO": self.gitsync_repo,
                            "GITSYNC_ROOT": container_context.workspace_parent,
                            "GITSYNC_LINK": container_context.workspace_name,
                        }
                        if self.gitsync_ref is not None:
                            git_sync_env["GITSYNC_REF"] = self.gitsync_ref
                        if self.gitsync_period is not None:
                            git_sync_env["GITSYNC_PERIOD"] = self.gitsync_period
                        if self.gitsync_env is not None:
                            git_sync_env.update(self.gitsync_env)
                        gitsync_container = CreateContainer(
                            container_name="git-sync",
                            app_name=self.get_app_name(),
                            image_name=self.gitsync_image_name,
                            image_tag=self.gitsync_image_tag,
                            env_vars=git_sync_env,
                            envs_from_configmap=[cm.cm_name for cm in config_maps] if len(config_maps) > 0 else None,
                            envs_from_secret=[secret.secret_name for secret in secrets] if len(secrets) > 0 else None,
                            volumes=[workspace_volume],
                        )
                        containers.append(gitsync_container)

                        if self.create_gitsync_init_container:
                            git_sync_init_env: Dict[str, str] = {"GITSYNC_ONE_TIME": "True"}
                            git_sync_init_env.update(git_sync_env)
                            _git_sync_init_container = CreateContainer(
                                container_name="git-sync-init",
                                app_name=gitsync_container.app_name,
                                image_name=gitsync_container.image_name,
                                image_tag=gitsync_container.image_tag,
                                env_vars=git_sync_init_env,
                                envs_from_configmap=gitsync_container.envs_from_configmap,
                                envs_from_secret=gitsync_container.envs_from_secret,
                                volumes=gitsync_container.volumes,
                            )
                            init_containers.append(_git_sync_init_container)
                    else:
                        logger.error("GITSYNC_REPO invalid")

            # If workspace_volume_type is HostPath
            elif self.workspace_volume_type == K8sWorkspaceVolumeType.HostPath:
                workspace_root_in_container = container_context.workspace_root
                workspace_root_on_host = str(self.workspace_root)
                logger.debug(f"Mounting: {workspace_root_on_host}")
                logger.debug(f"      to: {workspace_root_in_container}")
                workspace_volume = CreateVolume(
                    volume_name=workspace_volume_name,
                    app_name=self.get_app_name(),
                    mount_path=workspace_root_in_container,
                    volume_type=VolumeType.HOST_PATH,
                    host_path=HostPathVolumeSource(
                        path=workspace_root_on_host,
                    ),
                )
                volumes.append(workspace_volume)

        # NodeSelectors for Pods for creating az sensitive volumes
        pod_node_selector: Optional[Dict[str, str]] = self.pod_node_selector
        if self.create_volume:
            # Build volume_name
            volume_name = self.volume_name
            if volume_name is None:
                volume_name = get_default_volume_name(f"{self.get_app_name()}-{container_context.workspace_name}")

            # If volume_type is AwsEbs
            if self.volume_type == AppVolumeType.AwsEbs:
                if self.ebs_volume_id is not None or self.ebs_volume is not None:
                    # To use EbsVolume as the volume_type we:
                    # 1. Need the volume_id
                    # 2. Need to make sure pods are scheduled in the
                    #       same region/az as the volume

                    # For the volume_id we can either:
                    # 1. Use self.ebs_volume_id
                    # 2. OR get it from self.ebs_volume
                    ebs_volume_id = self.ebs_volume_id
                    # Derive ebs_volume_id from self.ebs_volume if needed
                    if ebs_volume_id is None and self.ebs_volume is not None:
                        from phi.aws.resource.ec2.volume import EbsVolume

                        # Validate self.ebs_volume is of type EbsVolume
                        if not isinstance(self.ebs_volume, EbsVolume):
                            raise ValueError(f"ebs_volume must be of type EbsVolume, found {type(self.ebs_volume)}")

                        ebs_volume_id = self.ebs_volume.get_volume_id()

                    logger.debug(f"ebs_volume_id: {ebs_volume_id}")
                    if ebs_volume_id is None:
                        logger.error(f"{self.get_app_name()}: ebs_volume_id not available, skipping app")
                        return []

                    logger.debug(f"Mounting: {volume_name}")
                    logger.debug(f"      to: {self.volume_container_path}")
                    ebs_volume = CreateVolume(
                        volume_name=volume_name,
                        app_name=self.get_app_name(),
                        mount_path=self.volume_container_path,
                        volume_type=VolumeType.AWS_EBS,
                        aws_ebs=AwsElasticBlockStoreVolumeSource(
                            volume_id=ebs_volume_id,
                        ),
                    )
                    volumes.append(ebs_volume)

                    # For the aws_region/az we can either:
                    # 1. Use self.ebs_volume_region
                    # 2. OR get it from self.ebs_volume
                    ebs_volume_region = self.ebs_volume_region
                    ebs_volume_az = self.ebs_volume_az
                    # Derive the aws_region from self.ebs_volume if needed
                    if ebs_volume_region is None and self.ebs_volume is not None:
                        from phi.aws.resource.ec2.volume import EbsVolume

                        # Validate self.ebs_volume is of type EbsVolume
                        if not isinstance(self.ebs_volume, EbsVolume):
                            raise ValueError(f"ebs_volume must be of type EbsVolume, found {type(self.ebs_volume)}")

                        _aws_region_from_ebs_volume = self.ebs_volume.get_aws_region()
                        if _aws_region_from_ebs_volume is not None:
                            ebs_volume_region = _aws_region_from_ebs_volume
                    # Derive the aws_region from this App if needed

                    # Derive the availability_zone from self.ebs_volume if needed
                    if ebs_volume_az is None and self.ebs_volume is not None:
                        from phi.aws.resource.ec2.volume import EbsVolume

                        # Validate self.ebs_volume is of type EbsVolume
                        if not isinstance(self.ebs_volume, EbsVolume):
                            raise ValueError(f"ebs_volume must be of type EbsVolume, found {type(self.ebs_volume)}")

                        ebs_volume_az = self.ebs_volume.availability_zone

                    logger.debug(f"ebs_volume_region: {ebs_volume_region}")
                    logger.debug(f"ebs_volume_az: {ebs_volume_az}")

                    # VERY IMPORTANT: pods should be scheduled in the same region/az as the volume
                    # To do this, we add NodeSelectors to Pods
                    if self.schedule_pods_in_ebs_topology:
                        if pod_node_selector is None:
                            pod_node_selector = {}

                        # Add NodeSelectors to Pods, so they are scheduled in the same
                        # region and zone as the ebs_volume
                        # https://kubernetes.io/docs/reference/labels-annotations-taints/#topologykubernetesiozone
                        if ebs_volume_region is not None:
                            pod_node_selector["topology.kubernetes.io/region"] = ebs_volume_region
                        else:
                            raise ValueError(
                                f"{self.get_app_name()}: ebs_volume_region not provided "
                                f"but needed for scheduling pods in the same region as the ebs_volume"
                            )

                        if ebs_volume_az is not None:
                            pod_node_selector["topology.kubernetes.io/zone"] = ebs_volume_az
                        else:
                            raise ValueError(
                                f"{self.get_app_name()}: ebs_volume_az not provided "
                                f"but needed for scheduling pods in the same zone as the ebs_volume"
                            )
                else:
                    raise ValueError(f"{self.get_app_name()}: ebs_volume_id not provided")

            # If volume_type is EmptyDir
            elif self.volume_type == AppVolumeType.EmptyDir:
                empty_dir_volume = CreateVolume(
                    volume_name=volume_name,
                    app_name=self.get_app_name(),
                    mount_path=self.volume_container_path,
                    volume_type=VolumeType.EMPTY_DIR,
                )
                volumes.append(empty_dir_volume)

            # If volume_type is HostPath
            elif self.volume_type == AppVolumeType.HostPath:
                if self.volume_host_path is not None:
                    volume_host_path_str = str(self.volume_host_path)
                    logger.debug(f"Mounting: {volume_host_path_str}")
                    logger.debug(f"      to: {self.volume_container_path}")
                    host_path_volume = CreateVolume(
                        volume_name=volume_name,
                        app_name=self.get_app_name(),
                        mount_path=self.volume_container_path,
                        volume_type=VolumeType.HOST_PATH,
                        host_path=HostPathVolumeSource(
                            path=volume_host_path_str,
                        ),
                    )
                    volumes.append(host_path_volume)
                else:
                    raise ValueError(f"{self.get_app_name()}: volume_host_path not provided")
            else:
                raise ValueError(f"{self.get_app_name()}: volume_type: {self.volume_type} not supported")

        # -*- Get Container Ports
        if self.open_port:
            container_port = CreatePort(
                name=self.container_port_name,
                container_port=self.container_port,
                service_port=self.service_port,
                target_port=self.service_target_port or self.container_port_name,
            )
            ports.append(container_port)

            # Validate NODE_PORT before adding it to the container_port
            # If ServiceType == NODE_PORT then validate self.service_node_port is available
            if self.service_type == ServiceType.NODE_PORT:
                if self.service_node_port is None or self.service_node_port < 30000 or self.service_node_port > 32767:
                    raise ValueError(f"NodePort: {self.service_node_port} invalid for ServiceType: {self.service_type}")
                else:
                    container_port.node_port = self.service_node_port
            # If ServiceType == LOAD_BALANCER then validate self.service_node_port only IF available
            elif self.service_type == ServiceType.LOAD_BALANCER:
                if self.service_node_port is not None:
                    if self.service_node_port < 30000 or self.service_node_port > 32767:
                        logger.warning(
                            f"NodePort: {self.service_node_port} invalid for ServiceType: {self.service_type}"
                        )
                        logger.warning("NodePort value will be ignored")
                        self.service_node_port = None
                    else:
                        container_port.node_port = self.service_node_port
            # else validate self.service_node_port is NOT available
            elif self.service_node_port is not None:
                logger.warning(
                    f"NodePort: {self.service_node_port} provided without specifying "
                    f"ServiceType as NODE_PORT or LOAD_BALANCER"
                )
                logger.warning("NodePort value will be ignored")
                self.service_node_port = None

        # -*- Get Container Labels
        container_labels: Dict[str, str] = self.get_container_labels(common_labels)

        # -*- Get Container Args: Equivalent to docker CMD
        container_args: Optional[List[str]] = self.get_container_args()
        if container_args:
            logger.debug("Command: {}".format(" ".join(container_args)))

        # -*- Build the Container
        container = CreateContainer(
            container_name=self.get_container_name(),
            app_name=self.get_app_name(),
            image_name=self.image_name,
            image_tag=self.image_tag,
            # Equivalent to docker images CMD
            args=container_args,
            # Equivalent to docker images ENTRYPOINT
            command=[self.entrypoint] if isinstance(self.entrypoint, str) else self.entrypoint,
            image_pull_policy=self.image_pull_policy or ImagePullPolicy.IF_NOT_PRESENT,
            envs_from_configmap=[cm.cm_name for cm in config_maps] if len(config_maps) > 0 else None,
            envs_from_secret=[secret.secret_name for secret in secrets] if len(secrets) > 0 else None,
            ports=ports if len(ports) > 0 else None,
            volumes=volumes if len(volumes) > 0 else None,
            labels=container_labels,
        )
        containers.insert(0, container)

        # Set default container for kubectl commands
        # https://kubernetes.io/docs/reference/labels-annotations-taints/#kubectl-kubernetes-io-default-container
        pod_annotations = {"kubectl.kubernetes.io/default-container": container.container_name}

        # -*- Add pod annotations
        if self.pod_annotations is not None and isinstance(self.pod_annotations, dict):
            pod_annotations.update(self.pod_annotations)

        # -*- Get Deployment Labels
        deploy_labels: Dict[str, str] = self.get_deployment_labels(common_labels)

        # If using EbsVolume, restart the deployment on update
        recreate_deployment_on_update = (
            True if (self.create_volume and self.volume_type == AppVolumeType.AwsEbs) else False
        )

        # -*- Create the Deployment
        deployment = CreateDeployment(
            deploy_name=self.get_deploy_name(),
            pod_name=self.get_pod_name(),
            app_name=self.get_app_name(),
            namespace=ns_name,
            service_account_name=sa_name,
            replicas=self.replicas,
            containers=containers,
            init_containers=init_containers if len(init_containers) > 0 else None,
            pod_node_selector=pod_node_selector,
            restart_policy=self.restart_policy or RestartPolicy.ALWAYS,
            termination_grace_period_seconds=self.termination_grace_period_seconds,
            volumes=volumes if len(volumes) > 0 else None,
            labels=deploy_labels,
            pod_annotations=pod_annotations,
            topology_spread_key=self.topology_spread_key,
            topology_spread_max_skew=self.topology_spread_max_skew,
            topology_spread_when_unsatisfiable=self.topology_spread_when_unsatisfiable,
            recreate_on_update=recreate_deployment_on_update,
        )
        deployments.append(deployment)

        # -*- Create the Service
        if self.create_service:
            service_labels = self.get_service_labels(common_labels)
            service_annotations = self.get_service_annotations()
            service = CreateService(
                service_name=self.get_service_name(),
                app_name=self.get_app_name(),
                namespace=ns_name,
                service_account_name=sa_name,
                service_type=self.service_type,
                deployment=deployment,
                ports=ports if len(ports) > 0 else None,
                labels=service_labels,
                annotations=service_annotations,
                # If ServiceType == ServiceType.LoadBalancer
                health_check_node_port=self.health_check_node_port,
                internal_traffic_policy=self.internal_traffic_policy,
                load_balancer_class=self.load_balancer_class,
                load_balancer_ip=self.load_balancer_ip,
                load_balancer_source_ranges=self.get_load_balancer_source_ranges(),
                allocate_load_balancer_node_ports=self.allocate_load_balancer_node_ports,
                protocol="https" if self.enable_https else "http",
            )
            services.append(service)

        # -*- Create the Ingress
        ingress: Optional[CreateIngress] = None
        if self.create_ingress:
            ingress_annotations = self.get_ingress_annotations()
            ingress_rules = self.get_ingress_rules()
            ingress = CreateIngress(
                ingress_name=self.get_ingress_name(),
                app_name=self.get_app_name(),
                namespace=ns_name,
                service_account_name=sa_name,
                annotations=ingress_annotations,
                ingress_class_name=self.ingress_class_name,
                rules=ingress_rules,
            )

        # -*- List of K8sResources created by this App
        app_resources: List[K8sResource] = []
        if ns:
            app_resources.append(ns.create())
        if sa:
            app_resources.append(sa.create())
        if cr:
            app_resources.append(cr.create())
        if crb:
            app_resources.append(crb.create())
        if len(secrets) > 0:
            app_resources.extend([secret.create() for secret in secrets])
        if len(config_maps) > 0:
            app_resources.extend([cm.create() for cm in config_maps])
        if len(services) > 0:
            app_resources.extend([service.create() for service in services])
        if len(deployments) > 0:
            app_resources.extend([deployment.create() for deployment in deployments])
        if ingress is not None:
            app_resources.append(ingress.create())
        if self.add_resources is not None and isinstance(self.add_resources, list):
            logger.debug(f"Adding {len(self.add_resources)} Resources")
            for resource in self.add_resources:
                if isinstance(resource, CreateK8sResource):
                    app_resources.append(resource.create())
                elif isinstance(resource, K8sResource):
                    app_resources.append(resource)
                else:
                    logger.error(f"Resource not of type K8sResource or CreateK8sResource: {resource}")
        add_app_resources = self.add_app_resources(namespace=ns_name, service_account_name=sa_name)
        if len(add_app_resources) > 0:
            logger.debug(f"Adding {len(add_app_resources)} App Resources")
            for r in add_app_resources:
                if isinstance(r, CreateK8sResource):
                    app_resources.append(r.create())
                elif isinstance(r, K8sResource):
                    app_resources.append(r)
                else:
                    logger.error(f"Resource not of type K8sResource or CreateK8sResource: {r}")
        if self.yaml_resources is not None and len(self.yaml_resources) > 0:
            logger.debug(f"Adding {len(self.yaml_resources)} YAML Resources")
            for yaml_resource in self.yaml_resources:
                if isinstance(yaml_resource, YamlResource):
                    app_resources.append(yaml_resource)

        logger.debug(f"------------ {self.get_app_name()} Built ------------")
        return app_resources

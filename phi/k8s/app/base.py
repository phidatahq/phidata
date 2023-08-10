from enum import Enum
from typing import Optional, Dict, Any, Union, List, TYPE_CHECKING

from phi.infra.app.base import InfraApp, WorkspaceVolumeType
from phi.infra.app.context import ContainerContext
from phi.k8s.app.context import K8sBuildContext
from phi.k8s.enums.restart_policy import RestartPolicy
from phi.k8s.enums.image_pull_policy import ImagePullPolicy
from phi.k8s.enums.service_type import ServiceType
from phi.utils.log import logger

if TYPE_CHECKING:
    from phi.k8s.resource.base import K8sResource


class AppVolumeType(str, Enum):
    HostPath = "HostPath"
    EmptyDir = "EmptyDir"
    AwsEbs = "AwsEbs"
    AwsEfs = "AwsEfs"
    PersistentVolume = "PersistentVolume"


class K8sApp(InfraApp):
    # -*- App Volume
    # Create a volume for container storage
    # Used for mounting app data like notebooks, models, etc.
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
    # -*- If volume_type=AppVolumeType.AwsEfs
    efs_volume_id: Optional[str] = None

    # Add NodeSelectors to Pods, so they are scheduled in the same region and zone as the ebs_volume
    schedule_pods_in_ebs_topology: bool = True

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
    deploy_restart_policy: Optional[RestartPolicy] = None
    deploy_labels: Optional[Dict[str, Any]] = None
    termination_grace_period_seconds: Optional[int] = None
    # Key to spread the pods across a topology
    topology_spread_key: Optional[str] = None
    # The degree to which pods may be unevenly distributed
    topology_spread_max_skew: Optional[int] = None
    # How to deal with a pod if it doesn't satisfy the spread constraint.
    topology_spread_when_unsatisfiable: Optional[str] = None

    # -*- Service Configuration
    create_service: bool = False
    service_name: Optional[str] = None
    service_type: Optional[ServiceType] = None
    # The port exposed by the service
    service_port: int = 8000
    # The node_port exposed by the service if service_type = ServiceType.NODE_PORT
    service_node_port: Optional[int] = None
    # The target_port is the port to access on the pods targeted by the service.
    # It can be the port number or port name on the pod.
    service_target_port: Optional[Union[str, int]] = None
    # Extra ports exposed by the webserver service. Type: List[CreatePort]
    service_ports: Optional[List[Any]] = None
    service_labels: Optional[Dict[str, Any]] = None
    service_annotations: Optional[Dict[str, str]] = None
    # If ServiceType == ServiceType.LoadBalancer
    service_health_check_node_port: Optional[int] = None
    service_internal_traffic_policy: Optional[str] = None
    service_load_balancer_class: Optional[str] = None
    service_load_balancer_ip: Optional[str] = None
    service_load_balancer_source_ranges: Optional[List[str]] = None
    service_allocate_load_balancer_node_ports: Optional[bool] = None

    # -*- Ingress Configuration
    create_ingress: bool = False
    ingress_name: Optional[str] = None
    ingress_annotations: Optional[Dict[str, str]] = None

    # -*- RBAC Configuration
    use_rbac: bool = False
    # Create a Namespace with name ns_name & default values
    ns_name: Optional[str] = None
    # or Provide the full Namespace definition
    # Type: CreateNamespace
    namespace: Optional[Any] = None
    # Create a ServiceAccount with name sa_name & default values
    sa_name: Optional[str] = None
    # or Provide the full ServiceAccount definition
    # Type: CreateServiceAccount
    service_account: Optional[Any] = None
    # Create a ClusterRole with name cr_name & default values
    cr_name: Optional[str] = None
    # or Provide the full ClusterRole definition
    # Type: CreateClusterRole
    cluster_role: Optional[Any] = None
    # Create a ClusterRoleBinding with name crb_name & default values
    crb_name: Optional[str] = None
    # or Provide the full ClusterRoleBinding definition
    # Type: CreateClusterRoleBinding
    cluster_role_binding: Optional[Any] = None

    # -*- Add additional Kubernetes resources to the App
    # Type: CreateSecret
    extra_secrets: Optional[List[Any]] = None
    # Type: CreateConfigMap
    extra_configmaps: Optional[List[Any]] = None
    # Type: CreateService
    extra_services: Optional[List[Any]] = None
    # Type: CreateDeployment
    extra_deployments: Optional[List[Any]] = None
    # Type: CreatePersistentVolume
    extra_pvs: Optional[List[Any]] = None
    # Type: CreatePVC
    extra_pvcs: Optional[List[Any]] = None
    # Type: CreateContainer
    extra_containers: Optional[List[Any]] = None
    # Type: CreateContainer
    extra_init_containers: Optional[List[Any]] = None
    # Type: CreatePort
    extra_ports: Optional[List[Any]] = None
    # Type: CreateVolume
    extra_volumes: Optional[List[Any]] = None
    # Type: CreateStorageClass
    extra_storage_classes: Optional[List[Any]] = None
    # Type: CreateCustomObject
    extra_custom_objects: Optional[List[Any]] = None
    # Type: CreateCustomResourceDefinition
    extra_crds: Optional[List[Any]] = None

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

    def get_service_port(self) -> int:
        return self.service_port

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

    def get_container_args(self) -> Optional[List[str]]:
        if isinstance(self.command, str):
            return self.command.strip().split(" ")
        return self.command

    def build_resources(self, build_context: K8sBuildContext) -> List["K8sResource"]:
        from phi.k8s.create.apiextensions_k8s_io.v1.custom_object import CreateCustomObject
        from phi.k8s.create.apiextensions_k8s_io.v1.custom_resource_definition import CreateCustomResourceDefinition
        from phi.k8s.create.apps.v1.deployment import CreateDeployment
        from phi.k8s.create.common.port import CreatePort
        from phi.k8s.create.core.v1.config_map import CreateConfigMap
        from phi.k8s.create.core.v1.container import CreateContainer
        from phi.k8s.create.core.v1.namespace import CreateNamespace
        from phi.k8s.create.core.v1.persistent_volume import CreatePersistentVolume
        from phi.k8s.create.core.v1.persistent_volume_claim import CreatePVC
        from phi.k8s.create.core.v1.secret import CreateSecret
        from phi.k8s.create.core.v1.service import CreateService
        from phi.k8s.create.core.v1.service_account import CreateServiceAccount
        from phi.k8s.create.core.v1.volume import (
            CreateVolume,
            HostPathVolumeSource,
            AwsElasticBlockStoreVolumeSource,
            VolumeType,
        )
        from phi.k8s.create.rbac_authorization_k8s_io.v1.cluste_role_binding import CreateClusterRoleBinding
        from phi.k8s.create.rbac_authorization_k8s_io.v1.cluster_role import CreateClusterRole
        from phi.k8s.create.storage_k8s_io.v1.storage_class import CreateStorageClass
        from phi.utils.defaults import get_default_volume_name, get_default_sa_name

        logger.debug(f"------------ Building {self.get_app_name()} ------------")
        # -*- Initialize K8s resources
        ns: Optional[CreateNamespace] = self.namespace
        sa: Optional[CreateServiceAccount] = self.service_account
        cr: Optional[CreateClusterRole] = self.cluster_role
        crb: Optional[CreateClusterRoleBinding] = self.cluster_role_binding
        secrets: List[CreateSecret] = self.extra_secrets or []
        config_maps: List[CreateConfigMap] = self.extra_configmaps or []
        services: List[CreateService] = self.extra_services or []
        deployments: List[CreateDeployment] = self.extra_deployments or []
        pvs: List[CreatePersistentVolume] = self.extra_pvs or []
        pvcs: List[CreatePVC] = self.extra_pvcs or []
        containers: List[CreateContainer] = self.extra_containers or []
        init_containers: List[CreateContainer] = self.extra_init_containers or []
        ports: List[CreatePort] = self.extra_ports or []
        volumes: List[CreateVolume] = self.extra_volumes or []
        storage_classes: List[CreateStorageClass] = self.extra_storage_classes or []
        custom_objects: List[CreateCustomObject] = self.extra_custom_objects or []
        crds: List[CreateCustomResourceDefinition] = self.extra_crds or []

        # -*- Namespace to use for this App
        # Use the Namespace provided by the App or the default from the build_context
        ns_name: str = self.ns_name or build_context.namespace

        # -*- Service Account to use for this App
        # Use the Service Account provided by the App or the default from the build_context
        sa_name: Optional[str] = self.sa_name or build_context.service_account_name

        # Use the labels from the build_context as common labels for all resources
        common_labels: Optional[Dict[str, str]] = build_context.labels

        # -*- Build separate RBAC when use_rbac is True
        if self.use_rbac:
            # Create Namespace
            if ns is None:
                ns = CreateNamespace(
                    ns=ns_name,
                    app_name=self.get_app_name(),
                    labels=common_labels,
                )
            ns_name = ns.ns

            # Create Service Account
            if sa is None:
                sa = CreateServiceAccount(
                    sa_name=sa_name or get_default_sa_name(self.get_app_name()),
                    app_name=self.get_app_name(),
                    namespace=ns_name,
                )
            sa_name = sa.sa_name

            # Create Cluster Role
            if cr is None:
                cr = CreateClusterRole(
                    cr_name=self.get_cr_name(),
                    rules=self.get_cr_policy_rules(),
                    app_name=self.get_app_name(),
                    labels=common_labels,
                )

            # Create ClusterRoleBinding
            if crb is None:
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
                if container_context.workspace_name is not None:
                    workspace_volume_name = get_default_volume_name(
                        f"{self.get_app_name()}-{container_context.workspace_name}-ws"
                    )
                else:
                    workspace_volume_name = get_default_volume_name(f"{self.get_app_name()}-ws")

            # If workspace_volume_type is None or EmptyDir
            if self.workspace_volume_type is None or self.workspace_volume_type == WorkspaceVolumeType.EmptyDir:
                workspace_parent_container_path_str = container_context.workspace_parent
                logger.debug("Creating EmptyDir")
                logger.debug(f"    at: {workspace_parent_container_path_str}")
                workspace_volume = CreateVolume(
                    volume_name=workspace_volume_name,
                    app_name=self.get_app_name(),
                    mount_path=workspace_parent_container_path_str,
                    volume_type=VolumeType.EMPTY_DIR,
                )
                volumes.append(workspace_volume)

                if self.create_git_sync_sidecar:
                    if self.git_sync_repo is not None:
                        git_sync_env = {
                            "GIT_SYNC_REPO": self.git_sync_repo,
                            "GIT_SYNC_ROOT": workspace_parent_container_path_str,
                            "GIT_SYNC_DEST": container_context.workspace_name,
                        }
                        if self.git_sync_branch is not None:
                            git_sync_env["GIT_SYNC_BRANCH"] = self.git_sync_branch
                        if self.git_sync_wait is not None:
                            git_sync_env["GIT_SYNC_WAIT"] = str(self.git_sync_wait)
                        git_sync_container = CreateContainer(
                            container_name="git-sync",
                            app_name=self.get_app_name(),
                            image_name=self.git_sync_image_name,
                            image_tag=self.git_sync_image_tag,
                            env=git_sync_env,
                            envs_from_configmap=[cm.cm_name for cm in config_maps] if len(config_maps) > 0 else None,
                            envs_from_secret=[secret.secret_name for secret in secrets] if len(secrets) > 0 else None,
                            volumes=[workspace_volume],
                        )
                        containers.append(git_sync_container)

                        if self.create_git_sync_init_container:
                            git_sync_init_env: Dict[str, Any] = {"GIT_SYNC_ONE_TIME": True}
                            git_sync_init_env.update(git_sync_env)
                            _git_sync_init_container = CreateContainer(
                                container_name="git-sync-init",
                                app_name=git_sync_container.app_name,
                                image_name=git_sync_container.image_name,
                                image_tag=git_sync_container.image_tag,
                                env=git_sync_init_env,
                                envs_from_configmap=git_sync_container.envs_from_configmap,
                                envs_from_secret=git_sync_container.envs_from_secret,
                                volumes=git_sync_container.volumes,
                            )
                            init_containers.append(_git_sync_init_container)
                    else:
                        logger.error("GIT_SYNC_REPO invalid")

            # If workspace_volume_type is HostPath
            elif self.workspace_volume_type == WorkspaceVolumeType.HostPath:
                workspace_root_path_str = str(self.workspace_root)
                workspace_root_container_path_str = container_context.workspace_root
                logger.debug(f"Mounting: {workspace_root_path_str}")
                logger.debug(f"      to: {workspace_root_container_path_str}")
                workspace_volume = CreateVolume(
                    volume_name=workspace_volume_name,
                    app_name=self.get_app_name(),
                    mount_path=workspace_root_container_path_str,
                    volume_type=VolumeType.HOST_PATH,
                    host_path=HostPathVolumeSource(
                        path=workspace_root_path_str,
                    ),
                )
                volumes.append(workspace_volume)

        # NodeSelectors for Pods for creating az sensitive volumes
        pod_node_selector: Optional[Dict[str, str]] = self.pod_node_selector
        if self.create_volume:
            # Build volume_name
            volume_name = self.volume_name
            if volume_name is None:
                if container_context.workspace_name is not None:
                    volume_name = get_default_volume_name(f"{self.get_app_name()}-{container_context.workspace_name}")
                else:
                    volume_name = get_default_volume_name(self.get_app_name())

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
                        raise ValueError("ebs_volume_id is None and could not be derived")

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
        if self.open_container_port:
            container_port = CreatePort(
                name=self.container_port_name,
                container_port=self.container_port,
                service_port=self.service_port,
                target_port=self.service_target_port or self.container_port_name,
            )
            ports.append(container_port)

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
            restart_policy=self.deploy_restart_policy or RestartPolicy.ALWAYS,
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
            service_labels: Dict[str, str] = self.get_service_labels(common_labels)
            service = CreateService(
                service_name=self.get_service_name(),
                app_name=self.get_app_name(),
                namespace=ns_name,
                service_account_name=sa_name,
                service_type=self.service_type,
                deployment=deployment,
                ports=ports if len(ports) > 0 else None,
                labels=service_labels,
            )
            services.append(service)

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
        if len(storage_classes) > 0:
            app_resources.extend([sc.create() for sc in storage_classes])
        if len(services) > 0:
            app_resources.extend([service.create() for service in services])
        if len(deployments) > 0:
            app_resources.extend([deployment.create() for deployment in deployments])
        if len(custom_objects) > 0:
            app_resources.extend([co.create() for co in custom_objects])
        if len(crds) > 0:
            app_resources.extend([crd.create() for crd in crds])
        if len(pvs) > 0:
            app_resources.extend([pv.create() for pv in pvs])
        if len(pvcs) > 0:
            app_resources.extend([pvc.create() for pvc in pvcs])

        logger.debug(f"------------ {self.get_app_name()} Built ------------")
        return app_resources

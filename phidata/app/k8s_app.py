from typing import Optional, Dict, Any, Union, List
from collections import OrderedDict

from phidata.app.base_app import (
    BaseApp,
    BaseAppArgs,
    WorkspaceVolumeType,
    AppVolumeType,
)
from phidata.k8s.enums.restart_policy import RestartPolicy
from phidata.k8s.enums.image_pull_policy import ImagePullPolicy
from phidata.k8s.enums.service_type import ServiceType
from phidata.types.context import ContainerPathContext
from phidata.utils.log import logger


class K8sAppArgs(BaseAppArgs):
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
    # The port exposed by the service.
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

    # Add additional Kubernetes resources to the App
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


class K8sApp(BaseApp):
    def __init__(self) -> None:
        super().__init__()

        # Args for the K8sApp, updated by the subclass
        self.args: K8sAppArgs = K8sAppArgs()

        # Dict of KubernetesResourceGroups
        # Type: Optional[Dict[str, K8sResourceGroup]]
        self.k8s_resource_groups: Optional[Dict[str, Any]] = None

    @property
    def container_name(self) -> str:
        from phidata.utils.k8s import get_default_container_name

        return self.args.container_name or get_default_container_name(self.name)

    @container_name.setter
    def container_name(self, container_name: str) -> None:
        if self.args is not None and container_name is not None:
            self.args.container_name = container_name

    @property
    def pod_name(self) -> str:
        from phidata.utils.k8s import get_default_pod_name

        return self.args.pod_name or get_default_pod_name(self.name)

    @pod_name.setter
    def pod_name(self, pod_name: str) -> None:
        if self.args is not None and pod_name is not None:
            self.args.pod_name = pod_name

    @property
    def secret_name(self) -> str:
        from phidata.utils.k8s import get_default_secret_name

        return self.args.secret_name or get_default_secret_name(self.name)

    @secret_name.setter
    def secret_name(self, secret_name: str) -> None:
        if self.args is not None and secret_name is not None:
            self.args.secret_name = secret_name

    @property
    def configmap_name(self) -> str:
        from phidata.utils.k8s import get_default_configmap_name

        return self.args.configmap_name or get_default_configmap_name(self.name)

    @configmap_name.setter
    def configmap_name(self, configmap_name: str) -> None:
        if self.args is not None and configmap_name is not None:
            self.args.configmap_name = configmap_name

    @property
    def deploy_name(self) -> str:
        from phidata.utils.k8s import get_default_deploy_name

        return self.args.deploy_name or get_default_deploy_name(self.name)

    @deploy_name.setter
    def deploy_name(self, deploy_name: str) -> None:
        if self.args is not None and deploy_name is not None:
            self.args.deploy_name = deploy_name

    @property
    def service_name(self) -> str:
        from phidata.utils.k8s import get_default_service_name

        return self.args.service_name or get_default_service_name(self.name)

    @service_name.setter
    def service_name(self, service_name: str) -> None:
        if self.args is not None and service_name is not None:
            self.args.service_name = service_name

    @property
    def service_port(self) -> int:
        return self.args.service_port

    @service_port.setter
    def service_port(self, service_port: int) -> None:
        if self.args is not None and service_port is not None:
            self.args.service_port = service_port

    @property
    def sa_name(self) -> str:
        from phidata.utils.k8s import get_default_sa_name

        return self.args.sa_name or get_default_sa_name(self.name)

    @sa_name.setter
    def sa_name(self, sa_name: str) -> None:
        if self.args is not None and sa_name is not None:
            self.args.sa_name = sa_name

    @property
    def cr_name(self) -> str:
        from phidata.utils.k8s import get_default_cr_name

        return self.args.cr_name or get_default_cr_name(self.name)

    @cr_name.setter
    def cr_name(self, cr_name: str) -> None:
        if self.args is not None and cr_name is not None:
            self.args.cr_name = cr_name

    @property
    def crb_name(self) -> str:
        from phidata.utils.k8s import get_default_crb_name

        return self.args.crb_name or get_default_crb_name(self.name)

    @crb_name.setter
    def crb_name(self, crb_name: str) -> None:
        if self.args is not None and crb_name is not None:
            self.args.crb_name = crb_name

    def build_cr_policy_rules(self) -> List[Any]:
        from phidata.k8s.create.rbac_authorization_k8s_io.v1.cluster_role import (
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

    def build_container_env_k8s(
        self, container_paths: ContainerPathContext
    ) -> Dict[str, str]:
        from phidata.constants import (
            PYTHONPATH_ENV_VAR,
            PHIDATA_RUNTIME_ENV_VAR,
            SCRIPTS_DIR_ENV_VAR,
            STORAGE_DIR_ENV_VAR,
            META_DIR_ENV_VAR,
            PRODUCTS_DIR_ENV_VAR,
            NOTEBOOKS_DIR_ENV_VAR,
            WORKFLOWS_DIR_ENV_VAR,
            WORKSPACE_ROOT_ENV_VAR,
            WORKSPACE_CONFIG_DIR_ENV_VAR,
        )

        # Container Environment
        container_env: Dict[str, str] = self.container_env or {}
        container_env.update(
            {
                PHIDATA_RUNTIME_ENV_VAR: "kubernetes",
                SCRIPTS_DIR_ENV_VAR: container_paths.scripts_dir or "",
                STORAGE_DIR_ENV_VAR: container_paths.storage_dir or "",
                META_DIR_ENV_VAR: container_paths.meta_dir or "",
                PRODUCTS_DIR_ENV_VAR: container_paths.products_dir or "",
                NOTEBOOKS_DIR_ENV_VAR: container_paths.notebooks_dir or "",
                WORKFLOWS_DIR_ENV_VAR: container_paths.workflows_dir or "",
                WORKSPACE_ROOT_ENV_VAR: container_paths.workspace_root or "",
                WORKSPACE_CONFIG_DIR_ENV_VAR: container_paths.workspace_config_dir
                or "",
                "INSTALL_REQUIREMENTS": str(self.args.install_requirements),
                "REQUIREMENTS_FILE_PATH": container_paths.requirements_file or "",
                "MOUNT_WORKSPACE": str(self.args.mount_workspace),
                "WORKSPACE_DIR_CONTAINER_PATH": str(
                    self.args.workspace_dir_container_path
                ),
                "PRINT_ENV_ON_LOAD": str(self.args.print_env_on_load),
            }
        )

        if self.args.set_python_path:
            python_path = self.args.python_path
            if python_path is None:
                python_path = container_paths.workspace_root
                if self.args.add_python_paths is not None:
                    python_path = "{}:{}".format(
                        python_path, ":".join(self.args.add_python_paths)
                    )
            if python_path is not None:
                container_env[PYTHONPATH_ENV_VAR] = python_path

        # Set aws env vars
        self.set_aws_env_vars(env_dict=container_env)

        # Update the container env using env_file
        env_data_from_file = self.get_env_data()
        if env_data_from_file is not None:
            container_env.update(
                {k: str(v) for k, v in env_data_from_file.items() if v is not None}
            )

        # Update the container env with user provided env
        # this overwrites any existing variables with the same key
        if self.args.env is not None and isinstance(self.args.env, dict):
            container_env.update(
                {k: str(v) for k, v in self.args.env.items() if v is not None}
            )

        return container_env

    def build_container_labels_k8s(
        self, common_labels: Optional[Dict[str, str]]
    ) -> Dict[str, str]:
        labels: Dict[str, str] = common_labels or {}
        if self.args.container_labels is not None and isinstance(
            self.args.container_labels, dict
        ):
            labels.update(self.args.container_labels)
        return labels

    def build_deployment_labels_k8s(
        self, common_labels: Optional[Dict[str, str]]
    ) -> Dict[str, str]:
        labels: Dict[str, str] = common_labels or {}
        if self.args.container_labels is not None and isinstance(
            self.args.container_labels, dict
        ):
            labels.update(self.args.container_labels)
        return labels

    def build_service_labels_k8s(
        self, common_labels: Optional[Dict[str, str]]
    ) -> Dict[str, str]:
        labels: Dict[str, str] = common_labels or {}
        if self.args.container_labels is not None and isinstance(
            self.args.container_labels, dict
        ):
            labels.update(self.args.container_labels)
        return labels

    def build_container_args_k8s(self) -> Optional[List[str]]:
        if isinstance(self.args.command, str):
            return self.args.command.strip().split(" ")
        return self.args.command

    def get_k8s_rg(self, k8s_build_context: Any) -> Optional[Any]:
        from phidata.k8s.create.common.port import CreatePort
        from phidata.k8s.create.core.v1.container import CreateContainer
        from phidata.k8s.create.core.v1.volume import (
            CreateVolume,
            HostPathVolumeSource,
            AwsElasticBlockStoreVolumeSource,
            VolumeType,
        )
        from phidata.k8s.create.group import (
            CreateK8sResourceGroup,
            CreateNamespace,
            CreateServiceAccount,
            CreateClusterRole,
            CreateClusterRoleBinding,
            CreateSecret,
            CreateConfigMap,
            CreateStorageClass,
            CreateService,
            CreateDeployment,
            CreateCustomObject,
            CreateCustomResourceDefinition,
            CreatePersistentVolume,
            CreatePVC,
        )
        from phidata.k8s.resource.group import K8sBuildContext
        from phidata.types.context import ContainerPathContext
        from phidata.utils.common import get_default_volume_name

        # -*- Build Container Paths
        container_paths: Optional[ContainerPathContext] = self.build_container_paths()
        if container_paths is None:
            raise Exception("Could not build Container Paths")
        # logger.debug(f"ContainerPaths: {container_paths.json(indent=2)}")

        app_name = self.name
        workspace_name = container_paths.workspace_name
        logger.debug(f"Building K8sResourceGroup: {app_name} for {workspace_name}")

        if k8s_build_context is None or not isinstance(
            k8s_build_context, K8sBuildContext
        ):
            logger.error("k8s_build_context must be a K8sBuildContext")
            return None

        # -*- Initialize K8s resources
        ns: Optional[CreateNamespace] = self.args.namespace
        sa: Optional[CreateServiceAccount] = self.args.service_account
        cr: Optional[CreateClusterRole] = self.args.cluster_role
        crb: Optional[CreateClusterRoleBinding] = self.args.cluster_role_binding
        secrets: List[CreateSecret] = self.args.extra_secrets or []
        config_maps: List[CreateConfigMap] = self.args.extra_configmaps or []
        services: List[CreateService] = self.args.extra_services or []
        deployments: List[CreateDeployment] = self.args.extra_deployments or []
        pvs: List[CreatePersistentVolume] = self.args.extra_pvs or []
        pvcs: List[CreatePVC] = self.args.extra_pvcs or []
        containers: List[CreateContainer] = self.args.extra_containers or []
        init_containers: List[CreateContainer] = self.args.extra_init_containers or []
        ports: List[CreatePort] = self.args.extra_ports or []
        volumes: List[CreateVolume] = self.args.extra_volumes or []
        storage_classes: List[CreateStorageClass] = (
            self.args.extra_storage_classes or []
        )
        custom_objects: List[CreateCustomObject] = self.args.extra_custom_objects or []
        crds: List[CreateCustomResourceDefinition] = self.args.extra_crds or []

        # Use the Namespace provided with the App or
        # use the default Namespace from the k8s_build_context
        ns_name: str = self.args.ns_name or k8s_build_context.namespace
        # Use the Service Account provided with the App or
        # use the default Service Account from the k8s_build_context
        sa_name: Optional[str] = (
            self.args.sa_name or k8s_build_context.service_account_name
        )
        common_labels: Optional[Dict[str, str]] = k8s_build_context.labels

        # -*- Build separate RBAC if use_rbac is True
        if self.args.use_rbac:
            # Create Namespace for this App
            if ns is None:
                ns = CreateNamespace(
                    ns=ns_name,
                    app_name=app_name,
                    labels=common_labels,
                )
            ns_name = ns.ns

            # Create Service Account for this App
            if sa is None:
                sa = CreateServiceAccount(
                    sa_name=sa_name or self.sa_name,
                    app_name=app_name,
                    namespace=ns_name,
                )
            sa_name = sa.sa_name

            # Create Cluster Role for this App
            if cr is None:
                cr = CreateClusterRole(
                    cr_name=self.cr_name,
                    rules=self.build_cr_policy_rules(),
                    app_name=app_name,
                    labels=common_labels,
                )

            # Create ClusterRoleBinding for this App
            if crb is None:
                crb = CreateClusterRoleBinding(
                    crb_name=self.crb_name,
                    cr_name=cr.cr_name,
                    service_account_name=sa.sa_name,
                    app_name=app_name,
                    namespace=ns_name,
                    labels=common_labels,
                )

        # -*- Build Container Environment
        container_env: Dict[str, str] = self.build_container_env_k8s(
            container_paths=container_paths
        )
        # Create a ConfigMap to set the Container Environment
        container_env_cm = CreateConfigMap(
            cm_name=self.configmap_name,
            app_name=app_name,
            namespace=ns_name,
            data=container_env,
            labels=common_labels,
        )
        config_maps.append(container_env_cm)

        # -*- Build Container Secrets
        container_secrets = self.get_secret_data()
        # Create a Secret to set the Container Secrets
        if container_secrets is not None:
            container_env_secret = CreateSecret(
                secret_name=self.secret_name,
                app_name=app_name,
                string_data=container_secrets,
                namespace=ns_name,
                labels=common_labels,
            )
            secrets.append(container_env_secret)

        # Add NodeSelectors to Pods for creating az sensitive volumes
        pod_node_selector: Optional[Dict[str, str]] = self.args.pod_node_selector
        # -*- Build Container Volumes
        if self.args.mount_workspace:
            workspace_volume_name = self.args.workspace_volume_name
            if workspace_volume_name is None:
                if workspace_name is not None:
                    workspace_volume_name = get_default_volume_name(
                        f"{app_name}-{workspace_name}-ws"
                    )
                else:
                    workspace_volume_name = get_default_volume_name(f"{app_name}-ws")
            # If workspace_volume_type is None or EmptyDir
            if (
                self.args.workspace_volume_type is None
                or self.args.workspace_volume_type == WorkspaceVolumeType.EmptyDir
            ):
                workspace_parent_container_path_str = container_paths.workspace_parent
                logger.debug(f"Creating EmptyDir")
                logger.debug(f"\tat: {workspace_parent_container_path_str}")
                workspace_volume = CreateVolume(
                    volume_name=workspace_volume_name,
                    app_name=app_name,
                    mount_path=workspace_parent_container_path_str,
                    volume_type=VolumeType.EMPTY_DIR,
                )
                volumes.append(workspace_volume)

                if self.args.create_git_sync_sidecar:
                    if self.args.git_sync_repo is not None:
                        git_sync_env = {
                            "GIT_SYNC_REPO": self.args.git_sync_repo,
                            "GIT_SYNC_ROOT": workspace_parent_container_path_str,
                            "GIT_SYNC_DEST": workspace_name,
                        }
                        if self.args.git_sync_branch is not None:
                            git_sync_env["GIT_SYNC_BRANCH"] = self.args.git_sync_branch
                        if self.args.git_sync_wait is not None:
                            git_sync_env["GIT_SYNC_WAIT"] = str(self.args.git_sync_wait)
                        git_sync_container = CreateContainer(
                            container_name="git-sync",
                            app_name=app_name,
                            image_name=self.args.git_sync_image_name,
                            image_tag=self.args.git_sync_image_tag,
                            env=git_sync_env,
                            envs_from_configmap=[cm.cm_name for cm in config_maps]
                            if len(config_maps) > 0
                            else None,
                            envs_from_secret=[secret.secret_name for secret in secrets]
                            if len(secrets) > 0
                            else None,
                            volumes=[workspace_volume],
                        )
                        containers.append(git_sync_container)

                        if self.args.create_git_sync_init_container:
                            git_sync_init_env: Dict[str, Any] = {
                                "GIT_SYNC_ONE_TIME": True
                            }
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
            # Use HostPath as WorkspaceVolumeType
            elif self.args.workspace_volume_type == WorkspaceVolumeType.HostPath:
                workspace_root_path_str = str(self.workspace_root_path)
                workspace_root_container_path_str = container_paths.workspace_root
                logger.debug(f"Mounting: {workspace_root_path_str}")
                logger.debug(f"\tto: {workspace_root_container_path_str}")
                workspace_volume = CreateVolume(
                    volume_name=workspace_volume_name,
                    app_name=app_name,
                    mount_path=workspace_root_container_path_str,
                    volume_type=VolumeType.HOST_PATH,
                    host_path=HostPathVolumeSource(
                        path=workspace_root_path_str,
                    ),
                )
                volumes.append(workspace_volume)

        if self.args.create_app_volume:
            app_volume_name = self.args.app_volume_name
            if app_volume_name is None:
                if workspace_name is not None:
                    volume_name = get_default_volume_name(
                        f"{app_name}-{workspace_name}"
                    )
                else:
                    volume_name = get_default_volume_name(app_name)
            # Use AwsEbs as AppVolumeType
            if self.args.app_volume_type == AppVolumeType.AwsEbs:
                if (
                    self.args.app_ebs_volume_id is not None
                    or self.args.app_ebs_volume is not None
                ):
                    # To use EbsVolume as the volume_type we:
                    # 1. Need the volume_id
                    # 2. Need to make sure pods are scheduled in the
                    #       same region/az as the volume

                    # For the volume_id we can either:
                    # 1. Use self.args.app_ebs_volume_id
                    # 2. OR get it from the self.args.app_ebs_volume
                    app_ebs_volume_id = self.args.app_ebs_volume_id

                    # For the aws_region/az we can either:
                    # 1. Use self.args.app_ebs_volume_region
                    # 2. OR get it from self.args.app_ebs_volume
                    # 3. OR get it from the BaseAppArgs
                    app_ebs_volume_region = self.args.app_ebs_volume_region
                    app_ebs_volume_az = self.args.app_ebs_volume_az

                    # Derive the aws_region from self.args.app_ebs_volume if needed
                    if (
                        app_ebs_volume_region is None
                        and self.args.app_ebs_volume is not None
                    ):
                        # Note: this will use the `$AWS_REGION` env var if set
                        _aws_region_from_ebs_volume = (
                            self.args.app_ebs_volume.get_aws_region()
                        )
                        if _aws_region_from_ebs_volume is not None:
                            app_ebs_volume_region = _aws_region_from_ebs_volume

                    # Get the aws_region from the BaseAppArgs
                    if app_ebs_volume_region is None:
                        app_ebs_volume_region = self.aws_region

                    # Derive the availability_zone from self.args.app_ebs_volume if needed
                    if (
                        app_ebs_volume_az is None
                        and self.args.app_ebs_volume is not None
                    ):
                        app_ebs_volume_az = self.args.app_ebs_volume.availability_zone

                    logger.debug(f"app_ebs_volume_region: {app_ebs_volume_region}")
                    logger.debug(f"app_ebs_volume_az: {app_ebs_volume_az}")

                    # Derive ebs_volume_id from self.args.app_ebs_volume if needed
                    if (
                        app_ebs_volume_id is None
                        and self.args.app_ebs_volume is not None
                    ):
                        app_ebs_volume_id = self.args.app_ebs_volume.get_volume_id(
                            aws_region=app_ebs_volume_region,
                            aws_profile=self.aws_profile,
                        )

                    logger.debug(f"app_ebs_volume_id: {app_ebs_volume_id}")
                    if app_ebs_volume_id is None:
                        logger.error("Could not find volume_id for AppEbsVolume")
                        return None

                    app_ebs_volume = CreateVolume(
                        volume_name=app_volume_name,
                        app_name=app_name,
                        mount_path=self.args.app_volume_container_path,
                        volume_type=VolumeType.AWS_EBS,
                        aws_ebs=AwsElasticBlockStoreVolumeSource(
                            volume_id=app_ebs_volume_id,
                        ),
                    )
                    volumes.append(app_ebs_volume)

                    # VERY IMPORTANT: pods should be scheduled in the same region/az as the volume
                    # To do this, we add NodeSelectors to Pods
                    if self.args.schedule_pods_in_ebs_topology:
                        if pod_node_selector is None:
                            pod_node_selector = {}

                        # Add NodeSelectors to Pods, so they are scheduled in the same
                        # region and zone as the ebs_volume
                        # https://kubernetes.io/docs/reference/labels-annotations-taints/#topologykubernetesiozone
                        if app_ebs_volume_region is not None:
                            pod_node_selector[
                                "topology.kubernetes.io/region"
                            ] = app_ebs_volume_region

                        if app_ebs_volume_az is not None:
                            pod_node_selector[
                                "topology.kubernetes.io/zone"
                            ] = app_ebs_volume_az
                else:
                    logger.error(f"{app_name}: app_ebs_volume not provided")
                    return None
            # Use EmptyDir as AppVolumeType
            elif self.args.app_volume_type == AppVolumeType.EmptyDir:
                empty_dir_volume = CreateVolume(
                    volume_name=app_volume_name,
                    app_name=app_name,
                    mount_path=self.args.app_volume_container_path,
                    volume_type=VolumeType.EMPTY_DIR,
                )
                volumes.append(empty_dir_volume)
            # Use HostPath as AppVolumeType
            elif self.args.app_volume_type == AppVolumeType.HostPath:
                if self.args.app_volume_host_path is not None:
                    volume_host_path_str = str(self.args.app_volume_host_path)
                    host_path_volume = CreateVolume(
                        volume_name=app_volume_name,
                        app_name=app_name,
                        mount_path=self.args.app_volume_container_path,
                        volume_type=VolumeType.HOST_PATH,
                        host_path=HostPathVolumeSource(
                            path=volume_host_path_str,
                        ),
                    )
                    volumes.append(host_path_volume)
                else:
                    logger.error(f"{app_name}: app_volume_host_path not provided")
                    return None

        # -*- Build Container Ports
        if self.args.open_container_port:
            container_port = CreatePort(
                name=self.args.container_port_name,
                container_port=self.args.container_port,
                service_port=self.args.service_port,
                target_port=self.args.service_target_port
                or self.args.container_port_name,
            )
            ports.append(container_port)

        # -*- Build Container Labels
        container_labels: Dict[str, str] = self.build_container_labels_k8s(
            common_labels
        )

        # -*- Build Container Args: Equivalent to docker CMD
        container_args: Optional[List[str]] = self.build_container_args_k8s()
        if container_args:
            logger.debug("Command: {}".format(" ".join(container_args)))

        # -*- Create the Container
        container = CreateContainer(
            container_name=self.container_name,
            app_name=app_name,
            image_name=self.args.image_name,
            image_tag=self.args.image_tag,
            # Equivalent to docker images CMD
            args=container_args,
            # Equivalent to docker images ENTRYPOINT
            command=[self.args.entrypoint]
            if isinstance(self.args.entrypoint, str)
            else self.args.entrypoint,
            image_pull_policy=self.args.image_pull_policy
            or ImagePullPolicy.IF_NOT_PRESENT,
            envs_from_configmap=[cm.cm_name for cm in config_maps]
            if len(config_maps) > 0
            else None,
            envs_from_secret=[secret.secret_name for secret in secrets]
            if len(secrets) > 0
            else None,
            ports=ports if len(ports) > 0 else None,
            volumes=volumes if len(volumes) > 0 else None,
            labels=container_labels,
        )
        containers.insert(0, container)

        # Set default container for kubectl commands
        # https://kubernetes.io/docs/reference/labels-annotations-taints/#kubectl-kubernetes-io-default-container
        pod_annotations = {
            "kubectl.kubernetes.io/default-container": container.container_name
        }

        # -*- Add pod annotations
        if self.args.pod_annotations is not None and isinstance(
            self.args.pod_annotations, dict
        ):
            pod_annotations.update(self.args.pod_annotations)

        # -*- Build Deployment Labels
        deploy_labels: Dict[str, str] = self.build_deployment_labels_k8s(common_labels)

        # If using EbsVolume, restart the deployment on update
        recreate_deployment_on_update = (
            True
            if (
                self.args.create_app_volume
                and self.args.app_volume_type == AppVolumeType.AwsEbs
            )
            else False
        )

        # -*- Create the Deployment
        deployment = CreateDeployment(
            deploy_name=self.deploy_name,
            pod_name=self.pod_name,
            app_name=app_name,
            namespace=ns_name,
            service_account_name=sa_name,
            replicas=self.args.replicas,
            containers=containers,
            init_containers=init_containers if len(init_containers) > 0 else None,
            pod_node_selector=pod_node_selector,
            restart_policy=self.args.deploy_restart_policy or RestartPolicy.ALWAYS,
            termination_grace_period_seconds=self.args.termination_grace_period_seconds,
            volumes=volumes if len(volumes) > 0 else None,
            labels=deploy_labels,
            pod_annotations=pod_annotations,
            topology_spread_key=self.args.topology_spread_key,
            topology_spread_max_skew=self.args.topology_spread_max_skew,
            topology_spread_when_unsatisfiable=self.args.topology_spread_when_unsatisfiable,
            recreate_on_update=recreate_deployment_on_update,
        )
        deployments.append(deployment)

        # -*- Create the Service
        if self.args.create_service:
            service_labels: Dict[str, str] = self.build_service_labels_k8s(
                common_labels
            )
            _service = CreateService(
                service_name=self.service_name,
                app_name=app_name,
                namespace=ns_name,
                service_account_name=sa_name,
                service_type=self.args.service_type,
                deployment=deployment,
                ports=ports if len(ports) > 0 else None,
                labels=service_labels,
            )
            services.append(_service)

        # -*- Create the K8sResourceGroup
        k8s_resource_group = CreateK8sResourceGroup(
            name=app_name,
            enabled=self.args.enabled,
            ns=ns,
            sa=sa,
            cr=cr,
            crb=crb,
            secrets=secrets if len(secrets) > 0 else None,
            config_maps=config_maps if len(config_maps) > 0 else None,
            storage_classes=storage_classes if len(storage_classes) > 0 else None,
            services=services if len(services) > 0 else None,
            deployments=deployments if len(deployments) > 0 else None,
            custom_objects=custom_objects if len(custom_objects) > 0 else None,
            crds=crds if len(crds) > 0 else None,
            pvs=pvs if len(pvs) > 0 else None,
            pvcs=pvcs if len(pvcs) > 0 else None,
        )

        return k8s_resource_group.create()

    def build_k8s_resource_groups(self, docker_build_context: Any) -> None:
        k8s_rg = self.get_k8s_rg(docker_build_context)
        if k8s_rg is not None:
            if self.k8s_resource_groups is None:
                self.k8s_resource_groups = OrderedDict()
            self.k8s_resource_groups[k8s_rg.name] = k8s_rg

    def get_k8s_resource_groups(
        self, k8s_build_context: Any, defer_api_calls: bool = False
    ) -> Optional[Dict[str, Any]]:
        if self.k8s_resource_groups is None:
            self.build_k8s_resource_groups(k8s_build_context)
        # # Comment out in production
        # if self.k8s_resource_groups:
        #     logger.debug("K8sResourceGroups:")
        #     for rg_name, rg in self.k8s_resource_groups.items():
        #         logger.debug(
        #             "{}:{}\n{}".format(rg_name, type(rg), rg)
        #         )
        return self.k8s_resource_groups

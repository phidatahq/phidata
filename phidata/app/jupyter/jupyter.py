from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from phidata.app.db import DbApp
from phidata.app.aws_app import AwsApp, AwsAppArgs
from phidata.app.docker_app import DockerApp, DockerAppArgs
from phidata.app.k8s_app import K8sApp, K8sAppArgs
from phidata.k8s.enums.image_pull_policy import ImagePullPolicy
from phidata.k8s.enums.restart_policy import RestartPolicy
from phidata.k8s.enums.service_type import ServiceType
from phidata.workspace.volume import WorkspaceVolumeType
from phidata.utils.enums import ExtendedEnum
from phidata.utils.log import logger


class JupyterVolumeType(ExtendedEnum):
    HostPath = "HostPath"
    EmptyDir = "EmptyDir"
    AwsEbs = "AwsEbs"
    AwsEfs = "AwsEfs"
    PersistentVolume = "PersistentVolume"


class JupyterLabArgs(AwsAppArgs, DockerAppArgs, K8sAppArgs):
    # -*- Jupyter Configuration
    # Absolute path to JUPYTER_CONFIG_FILE,
    # Also used to set the JUPYTER_CONFIG_FILE env var,
    # This value is appended to the command using `--config`,
    jupyter_config_file: Optional[str] = None
    # Absolute path to the notebook directory,
    # Defaults to the workspace_root if mount_workspace = True else "/",
    notebook_dir: Optional[str] = None


class JupyterLab(AwsApp, DockerApp, K8sApp):
    def __init__(
        self,
        name: str = "jupyter",
        version: str = "1",
        enabled: bool = True,
        # -*- Jupyter Configuration,
        # Absolute path to JUPYTER_CONFIG_FILE,
        # Also used to set the JUPYTER_CONFIG_FILE env var,
        jupyter_config_file: str = "/resources/jupyter_lab_config.py",
        # Absolute path to the notebook directory,
        # Defaults to the workspace_root if mount_workspace = True else "/",
        notebook_dir: Optional[str] = None,
        # -*- Image Configuration,
        # Image can be provided as a DockerImage object or as image_name:image_tag
        image: Optional[Any] = None,
        image_name: str = "phidata/jupyter",
        image_tag: str = "3.6.3",
        entrypoint: Optional[Union[str, List[str]]] = None,
        command: Union[str, List[str]] = "jupyter lab",
        # -*- Debug Mode
        debug_mode: bool = False,
        # -*- Python Configuration,
        # Install python dependencies using a requirements.txt file,
        install_requirements: bool = False,
        # Path to the requirements.txt file relative to the workspace_root,
        requirements_file: str = "requirements.txt",
        # Set the PYTHONPATH env var,
        set_python_path: bool = False,
        # Manually provide the PYTHONPATH,
        python_path: Optional[str] = None,
        # Add paths to the PYTHONPATH env var,
        # If python_path is provided, this value is ignored,
        add_python_paths: Optional[List[str]] = None,
        # -*- Container Environment,
        # Add env variables to container,
        env: Optional[Dict[str, Any]] = None,
        # Read env variables from a file in yaml format,
        env_file: Optional[Path] = None,
        # Add secret variables to container,
        secrets: Optional[Dict[str, Any]] = None,
        # Read secret variables from a file in yaml format,
        secrets_file: Optional[Path] = None,
        # Read secret variables from AWS Secrets,
        aws_secrets: Optional[Any] = None,
        # -*- Container Ports,
        # Open a container port if open_container_port=True,
        open_container_port: bool = True,
        # Port number on the container,
        container_port: int = 8888,
        # Port name (only used by the K8sContainer),
        container_port_name: str = "http",
        # Host port to map to the container port,
        container_host_port: int = 8888,
        # -*- Workspace Volume,
        # Mount the workspace directory on the container,
        mount_workspace: bool = False,
        workspace_volume_name: Optional[str] = None,
        workspace_volume_type: Optional[WorkspaceVolumeType] = None,
        # Path to mount the workspace volume inside the container,
        workspace_dir_container_path: str = "/mnt/workspaces",
        # Add the workspace name to the container path,
        add_workspace_name_to_container_path: bool = True,
        # -*- If workspace_volume_type=WorkspaceVolumeType.HostPath,
        # Mount workspace_dir to workspace_dir_container_path,
        # If None, use the workspace_root,
        workspace_dir: Optional[str] = None,
        # -*- Resources Volume,
        # Mount a resources directory on the container,
        mount_resources: bool = False,
        # Resources directory relative to the workspace_root,
        resources_dir: str = "workspace/jupyter/resources",
        # Path to mount the resources_dir,
        resources_dir_container_path: str = "/mnt/resources",
        # -*- Jupyter Volume,
        # Create a volume for mounting notebooks, workspaces, etc.,
        # With jupyter, we cannot use git-sync as git-sync cannot upload changes to git,
        # So we mount a separate volume that provides persistent storage,
        create_volume: bool = True,
        volume_name: Optional[str] = None,
        volume_type: JupyterVolumeType = JupyterVolumeType.EmptyDir,
        # Path to mount the volume inside the container,
        volume_container_path: str = "/mnt",
        # -*- If volume_type=JupyterVolumeType.HostPath,
        volume_host_path: Optional[str] = None,
        # -*- If volume_type=JupyterVolumeType.AwsEbs,
        # EbsVolume: used to derive the volume_id, region, and az,
        ebs_volume: Optional[Any] = None,
        ebs_volume_region: Optional[str] = None,
        ebs_volume_az: Optional[str] = None,
        # Provide Ebs Volume-id manually,
        ebs_volume_id: Optional[str] = None,
        # Add NodeSelectors to Pods, so they are scheduled in the same region and zone as the ebs_volume,
        schedule_pods_in_ebs_topology: bool = True,
        # -*- If volume_type=JupyterVolumeType.PersistentVolume,
        # AccessModes is a list of ways the volume can be mounted.,
        # More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes#access-modes,
        # Type: phidata.infra.k8s.enums.pv.PVAccessMode,
        pv_access_modes: Optional[List[Any]] = None,
        pv_requests_storage: Optional[str] = None,
        # A list of mount options, e.g. ["ro", "soft"]. Not validated - mount will simply fail if one is invalid.,
        # More info: https://kubernetes.io/docs/concepts/storage/persistent-volumes/#mount-options,
        pv_mount_options: Optional[List[str]] = None,
        # What happens to a persistent volume when released from its claim.,
        #   The default policy is Retain.,
        # Literal["Delete", "Recycle", "Retain"],
        pv_reclaim_policy: Optional[str] = None,
        pv_storage_class: str = "",
        pv_labels: Optional[Dict[str, str]] = None,
        # -*- If volume_type=JupyterVolumeType.AwsEfs,
        efs_volume_id: Optional[str] = None,
        # Create a volume for mounting notebooks, workspaces, etc.,
        # With jupyter, we cannot use git-sync as git-sync cannot upload changes to git,
        # So we mount a volume that provides persistent storage,
        # -*- Container Configuration,
        container_name: Optional[str] = None,
        # Run container in the background and return a Container object.,
        container_detach: bool = True,
        # Enable auto-removal of the container on daemon side when the container’s process exits.,
        container_auto_remove: bool = True,
        # Remove the container when it has finished running. Default: True.,
        container_remove: bool = True,
        # Username or UID to run commands as inside the container.,
        container_user: Optional[Union[str, int]] = None,
        # Keep STDIN open even if not attached.,
        container_stdin_open: bool = True,
        # Return logs from STDOUT when container_detach=False.,
        container_stdout: Optional[bool] = True,
        # Return logs from STDERR when container_detach=False.,
        container_stderr: Optional[bool] = True,
        container_tty: bool = True,
        # Specify a test to perform to check that the container is healthy.,
        container_healthcheck: Optional[Dict[str, Any]] = None,
        # Optional hostname for the container.,
        container_hostname: Optional[str] = None,
        # Platform in the format os[/arch[/variant]].,
        container_platform: Optional[str] = None,
        # Path to the working directory.,
        container_working_dir: Optional[str] = None,
        # Add labels to the container,
        container_labels: Optional[Dict[str, Any]] = None,
        # Restart the container when it exits. Configured as a dictionary with keys:,
        # Name: One of on-failure, or always.,
        # MaximumRetryCount: Number of times to restart the container on failure.,
        # For example: {"Name": "on-failure", "MaximumRetryCount": 5},
        container_restart_policy: Optional[Dict[str, Any]] = None,
        # Add volumes to DockerContainer,
        # container_volumes is a dictionary which adds the volumes to mount,
        # inside the container. The key is either the host path or a volume name,,
        # and the value is a dictionary with 2 keys:,
        #   bind - The path to mount the volume inside the container,
        #   mode - Either rw to mount the volume read/write, or ro to mount it read-only.,
        # For example:,
        # {,
        #   '/home/user1/': {'bind': '/mnt/vol2', 'mode': 'rw'},,
        #   '/var/www': {'bind': '/mnt/vol1', 'mode': 'ro'},
        # },
        container_volumes: Optional[Dict[str, dict]] = None,
        # Add ports to DockerContainer,
        # The keys of the dictionary are the ports to bind inside the container,,
        # either as an integer or a string in the form port/protocol, where the protocol is either tcp, udp.,
        # The values of the dictionary are the corresponding ports to open on the host, which can be either:,
        #   - The port number, as an integer.,
        #       For example, {'2222/tcp': 3333} will expose port 2222 inside the container as port 3333 on the host.,
        #   - None, to assign a random host port. For example, {'2222/tcp': None}.,
        #   - A tuple of (address, port) if you want to specify the host interface.,
        #       For example, {'1111/tcp': ('127.0.0.1', 1111)}.,
        #   - A list of integers, if you want to bind multiple host ports to a single container port.,
        #       For example, {'1111/tcp': [1234, 4567]}.,
        container_ports: Optional[Dict[str, Any]] = None,
        # -*- Pod Configuration,
        pod_name: Optional[str] = None,
        pod_annotations: Optional[Dict[str, str]] = None,
        pod_node_selector: Optional[Dict[str, str]] = None,
        # -*- Secret Configuration,
        secret_name: Optional[str] = None,
        # -*- Configmap Configuration,
        configmap_name: Optional[str] = None,
        # -*- Deployment Configuration,
        replicas: int = 1,
        deploy_name: Optional[str] = None,
        # Type: ImagePullPolicy,
        image_pull_policy: Optional[Any] = None,
        # Type: RestartPolicy,
        deploy_restart_policy: Optional[Any] = None,
        deploy_labels: Optional[Dict[str, Any]] = None,
        termination_grace_period_seconds: Optional[int] = None,
        # Key to spread the pods across a topology,
        topology_spread_key: Optional[str] = None,
        # The degree to which pods may be unevenly distributed,
        topology_spread_max_skew: Optional[int] = None,
        # How to deal with a pod if it doesn't satisfy the spread constraint.,
        topology_spread_when_unsatisfiable: Optional[str] = None,
        # -*- Service Configuration,
        create_service: bool = False,
        service_name: Optional[str] = None,
        # Type: ServiceType,
        service_type: Optional[Any] = None,
        # The port exposed by the service.,
        service_port: int = 8000,
        # The node_port exposed by the service if service_type = ServiceType.NODE_PORT,
        service_node_port: Optional[int] = None,
        # The target_port is the port to access on the pods targeted by the service.,
        # It can be the port number or port name on the pod.,
        service_target_port: Optional[Union[str, int]] = None,
        # Extra ports exposed by the webserver service. Type: List[CreatePort],
        service_ports: Optional[List[Any]] = None,
        service_labels: Optional[Dict[str, Any]] = None,
        service_annotations: Optional[Dict[str, str]] = None,
        # If ServiceType == ServiceType.LoadBalancer,
        service_health_check_node_port: Optional[int] = None,
        service_internal_traffic_policy: Optional[str] = None,
        service_load_balancer_class: Optional[str] = None,
        service_load_balancer_ip: Optional[str] = None,
        service_load_balancer_source_ranges: Optional[List[str]] = None,
        service_allocate_load_balancer_node_ports: Optional[bool] = None,
        # -*- Ingress Configuration,
        create_ingress: bool = False,
        ingress_name: Optional[str] = None,
        ingress_annotations: Optional[Dict[str, str]] = None,
        # -*- RBAC Configuration,
        use_rbac: bool = False,
        # Create a Namespace with name ns_name & default values,
        ns_name: Optional[str] = None,
        # or Provide the full Namespace definition,
        # Type: CreateNamespace,
        namespace: Optional[Any] = None,
        # Create a ServiceAccount with name sa_name & default values,
        sa_name: Optional[str] = None,
        # or Provide the full ServiceAccount definition,
        # Type: CreateServiceAccount,
        service_account: Optional[Any] = None,
        # Create a ClusterRole with name cr_name & default values,
        cr_name: Optional[str] = None,
        # or Provide the full ClusterRole definition,
        # Type: CreateClusterRole,
        cluster_role: Optional[Any] = None,
        # Create a ClusterRoleBinding with name crb_name & default values,
        crb_name: Optional[str] = None,
        # or Provide the full ClusterRoleBinding definition,
        # Type: CreateClusterRoleBinding,
        cluster_role_binding: Optional[Any] = None,
        # -*- AWS Configuration,
        aws_subnets: Optional[List[str]] = None,
        aws_security_groups: Optional[List[str]] = None,
        # -*- ECS Configuration,
        ecs_cluster: Optional[Any] = None,
        ecs_launch_type: str = "FARGATE",
        ecs_task_cpu: str = "512",
        ecs_task_memory: str = "1024",
        ecs_service_count: int = 1,
        assign_public_ip: bool = True,
        ecs_enable_exec: bool = True,
        # -*- LoadBalancer Configuration,
        enable_load_balancer: bool = True,
        load_balancer: Optional[Any] = None,
        # HTTP or HTTPS,
        load_balancer_protocol: str = "HTTP",
        # Default 80 for HTTP and 443 for HTTPS,
        load_balancer_port: Optional[int] = None,
        load_balancer_certificate_arn: Optional[str] = None,
        #  -*- Resource Control,
        skip_create: bool = False,
        skip_read: bool = False,
        skip_update: bool = False,
        recreate_on_update: bool = False,
        skip_delete: bool = False,
        wait_for_creation: bool = True,
        wait_for_update: bool = True,
        wait_for_deletion: bool = True,
        waiter_delay: int = 30,
        waiter_max_attempts: int = 50,
        # Skip creation if resource with the same name is active,
        use_cache: bool = True,
        #  -*- Other args,
        print_env_on_load: bool = False,
        # Extra kwargs used to capture additional args,
        **extra_kwargs,
    ):
        super().__init__()

        if jupyter_config_file is not None:
            self.container_env = {"JUPYTER_CONFIG_FILE": jupyter_config_file}

        try:
            self.args: JupyterLabArgs = JupyterLabArgs(
                name=name,
                version=version,
                enabled=enabled,
                jupyter_config_file=jupyter_config_file,
                notebook_dir=notebook_dir,
                image=image,
                image_name=image_name,
                image_tag=image_tag,
                entrypoint=entrypoint,
                command=command,
                debug_mode=debug_mode,
                install_requirements=install_requirements,
                requirements_file=requirements_file,
                set_python_path=set_python_path,
                python_path=python_path,
                add_python_paths=add_python_paths,
                env=env,
                env_file=env_file,
                secrets=secrets,
                secrets_file=secrets_file,
                aws_secrets=aws_secrets,
                open_container_port=open_container_port,
                container_port=container_port,
                container_port_name=container_port_name,
                container_host_port=container_host_port,
                mount_workspace=mount_workspace,
                workspace_volume_name=workspace_volume_name,
                workspace_volume_type=workspace_volume_type,
                workspace_dir_container_path=workspace_dir_container_path,
                add_workspace_name_to_container_path=add_workspace_name_to_container_path,
                workspace_dir=workspace_dir,
                mount_resources=mount_resources,
                resources_dir=resources_dir,
                resources_dir_container_path=resources_dir_container_path,
                create_volume=create_volume,
                volume_name=volume_name,
                volume_type=volume_type,
                volume_container_path=volume_container_path,
                volume_host_path=volume_host_path,
                ebs_volume=ebs_volume,
                ebs_volume_region=ebs_volume_region,
                ebs_volume_az=ebs_volume_az,
                ebs_volume_id=ebs_volume_id,
                schedule_pods_in_ebs_topology=schedule_pods_in_ebs_topology,
                pv_access_modes=pv_access_modes,
                pv_requests_storage=pv_requests_storage,
                pv_mount_options=pv_mount_options,
                pv_reclaim_policy=pv_reclaim_policy,
                pv_storage_class=pv_storage_class,
                pv_labels=pv_labels,
                efs_volume_id=efs_volume_id,
                container_name=container_name,
                container_detach=container_detach,
                container_auto_remove=container_auto_remove,
                container_remove=container_remove,
                container_user=container_user,
                container_stdin_open=container_stdin_open,
                container_stdout=container_stdout,
                container_stderr=container_stderr,
                container_tty=container_tty,
                container_healthcheck=container_healthcheck,
                container_hostname=container_hostname,
                container_platform=container_platform,
                container_working_dir=container_working_dir,
                container_labels=container_labels,
                container_restart_policy=container_restart_policy,
                container_volumes=container_volumes,
                container_ports=container_ports,
                pod_name=pod_name,
                pod_annotations=pod_annotations,
                pod_node_selector=pod_node_selector,
                secret_name=secret_name,
                configmap_name=configmap_name,
                replicas=replicas,
                deploy_name=deploy_name,
                image_pull_policy=image_pull_policy,
                deploy_restart_policy=deploy_restart_policy,
                deploy_labels=deploy_labels,
                termination_grace_period_seconds=termination_grace_period_seconds,
                topology_spread_key=topology_spread_key,
                topology_spread_max_skew=topology_spread_max_skew,
                topology_spread_when_unsatisfiable=topology_spread_when_unsatisfiable,
                create_service=create_service,
                service_name=service_name,
                service_type=service_type,
                service_port=service_port,
                service_node_port=service_node_port,
                service_target_port=service_target_port,
                service_ports=service_ports,
                service_labels=service_labels,
                service_annotations=service_annotations,
                service_health_check_node_port=service_health_check_node_port,
                service_internal_traffic_policy=service_internal_traffic_policy,
                service_load_balancer_class=service_load_balancer_class,
                service_load_balancer_ip=service_load_balancer_ip,
                service_load_balancer_source_ranges=service_load_balancer_source_ranges,
                service_allocate_load_balancer_node_ports=service_allocate_load_balancer_node_ports,
                create_ingress=create_ingress,
                ingress_name=ingress_name,
                ingress_annotations=ingress_annotations,
                use_rbac=use_rbac,
                ns_name=ns_name,
                namespace=namespace,
                sa_name=sa_name,
                service_account=service_account,
                cr_name=cr_name,
                cluster_role=cluster_role,
                crb_name=crb_name,
                cluster_role_binding=cluster_role_binding,
                aws_subnets=aws_subnets,
                aws_security_groups=aws_security_groups,
                ecs_cluster=ecs_cluster,
                ecs_launch_type=ecs_launch_type,
                ecs_task_cpu=ecs_task_cpu,
                ecs_task_memory=ecs_task_memory,
                ecs_service_count=ecs_service_count,
                assign_public_ip=assign_public_ip,
                ecs_enable_exec=ecs_enable_exec,
                enable_load_balancer=enable_load_balancer,
                load_balancer=load_balancer,
                load_balancer_protocol=load_balancer_protocol,
                load_balancer_port=load_balancer_port,
                load_balancer_certificate_arn=load_balancer_certificate_arn,
                skip_create=skip_create,
                skip_read=skip_read,
                skip_update=skip_update,
                recreate_on_update=recreate_on_update,
                skip_delete=skip_delete,
                wait_for_creation=wait_for_creation,
                wait_for_update=wait_for_update,
                wait_for_deletion=wait_for_deletion,
                waiter_delay=waiter_delay,
                waiter_max_attempts=waiter_max_attempts,
                use_cache=use_cache,
                print_env_on_load=print_env_on_load,
                extra_kwargs=extra_kwargs,
            )
        except Exception as e:
            logger.error(f"Args for {self.name} are not valid: {e}")
            raise

    def get_container_command_docker(self) -> Optional[List[str]]:
        container_cmd: List[str]
        if isinstance(self.args.command, str):
            container_cmd = self.args.command.split(" ")
        elif isinstance(self.args.command, list):
            container_cmd = self.args.command
        else:
            container_cmd = []

        if self.args.jupyter_config_file is not None:
            container_cmd.append(f"--config={str(self.args.jupyter_config_file)}")

        if self.args.notebook_dir is None:
            if self.args.mount_workspace:
                if (
                    self.container_paths is not None
                    and self.container_paths.workspace_root is not None
                ):
                    container_cmd.append(
                        f"--notebook-dir={str(self.container_paths.workspace_root)}"
                    )
            else:
                container_cmd.append("--notebook-dir=/")
        else:
            container_cmd.append(f"--notebook-dir={str(self.args.notebook_dir)}")
        return container_cmd

    ######################################################
    ## K8s Resources
    ######################################################

    def get_k8s_rg(self, k8s_build_context: Any) -> Optional[Any]:
        app_name = self.args.name
        logger.debug(f"Building {app_name} K8sResourceGroup")

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
            WORKSPACES_MOUNT_ENV_VAR,
            WORKSPACE_CONFIG_DIR_ENV_VAR,
            INIT_AIRFLOW_ENV_VAR,
            AIRFLOW_ENV_ENV_VAR,
            AIRFLOW_DAGS_FOLDER_ENV_VAR,
            AIRFLOW_EXECUTOR_ENV_VAR,
            AIRFLOW_DB_CONN_URL_ENV_VAR,
        )
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

        if k8s_build_context is None or not isinstance(
            k8s_build_context, K8sBuildContext
        ):
            logger.error("k8s_build_context must be a K8sBuildContext")
            return None

        # Workspace paths
        if self.workspace_root_path is None:
            logger.error("Invalid workspace_root_path")
            return None

        workspace_name = self.workspace_root_path.stem
        container_paths: Optional[ContainerPathContext] = self.get_container_paths()
        if container_paths is None:
            logger.error("Could not build container paths")
            return None
        logger.debug(f"Container Paths: {container_paths.json(indent=2)}")

        # Init K8s resources for the CreateK8sResourceGroup
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

        # Common variables used by all resources
        # Use the Namespace provided with the App or
        # use the default Namespace from the k8s_build_context
        ns_name: str = self.args.ns_name or k8s_build_context.namespace
        sa_name: Optional[str] = (
            self.args.sa_name or k8s_build_context.service_account_name
        )
        common_labels: Optional[Dict[str, str]] = k8s_build_context.labels

        # -*- Use K8s RBAC
        # If use_rbac is True, use separate RBAC for this App
        # Create a namespace, service account, cluster role and cluster role binding
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
                    sa_name=sa_name or self.get_sa_name(),
                    app_name=app_name,
                    namespace=ns_name,
                )
            sa_name = sa.sa_name

            # Create Cluster Role for this App
            from phidata.k8s.create.rbac_authorization_k8s_io.v1.cluster_role import (
                PolicyRule,
            )

            if cr is None:
                cr = CreateClusterRole(
                    cr_name=self.args.cr_name or self.get_cr_name(),
                    rules=[
                        PolicyRule(
                            api_groups=[""],
                            resources=[
                                "pods",
                                "secrets",
                                "configmaps",
                            ],
                            verbs=[
                                "get",
                                "list",
                                "watch",
                                "create",
                                "update",
                                "patch",
                                "delete",
                            ],
                        ),
                        PolicyRule(
                            api_groups=[""],
                            resources=[
                                "pods/logs",
                            ],
                            verbs=[
                                "get",
                                "list",
                            ],
                        ),
                        # PolicyRule(
                        #     api_groups=[""],
                        #     resources=[
                        #         "pods/exec",
                        #     ],
                        #     verbs=[
                        #         "get",
                        #         "create",
                        #     ],
                        # ),
                    ],
                    app_name=app_name,
                    labels=common_labels,
                )

            # Create ClusterRoleBinding for this App
            if crb is None:
                crb = CreateClusterRoleBinding(
                    crb_name=self.args.crb_name or self.get_crb_name(),
                    cr_name=cr.cr_name,
                    service_account_name=sa.sa_name,
                    app_name=app_name,
                    namespace=ns_name,
                    labels=common_labels,
                )

        # Container pythonpath
        python_path = (
            self.args.python_path
            or f"{str(container_paths.workspace_root)}:{self.args.resources_dir_container_path}"
        )

        # Container Environment
        container_env: Dict[str, Any] = {
            # Env variables used by data workflows and data assets
            PYTHONPATH_ENV_VAR: python_path,
            PHIDATA_RUNTIME_ENV_VAR: "kubernetes",
            SCRIPTS_DIR_ENV_VAR: container_paths.scripts_dir,
            STORAGE_DIR_ENV_VAR: container_paths.storage_dir,
            META_DIR_ENV_VAR: container_paths.meta_dir,
            PRODUCTS_DIR_ENV_VAR: container_paths.products_dir,
            NOTEBOOKS_DIR_ENV_VAR: container_paths.notebooks_dir,
            WORKFLOWS_DIR_ENV_VAR: container_paths.workflows_dir,
            WORKSPACE_ROOT_ENV_VAR: container_paths.workspace_root,
            WORKSPACES_MOUNT_ENV_VAR: container_paths.workspace_parent,
            WORKSPACE_CONFIG_DIR_ENV_VAR: container_paths.workspace_config_dir,
            "INSTALL_REQUIREMENTS": str(self.args.install_requirements),
            "REQUIREMENTS_FILE_PATH": container_paths.requirements_file,
            "MOUNT_EBS_VOLUME": str(self.args.mount_ebs_volume),
            "MOUNT_WORKSPACE": str(self.args.mount_workspace),
            "MOUNT_RESOURCES": str(self.args.mount_resources),
            # Print env when the container starts
            "PRINT_ENV_ON_LOAD": str(self.args.print_env_on_load),
        }

        # Set airflow env vars
        self.set_aws_env_vars(env_dict=container_env)

        # Set JUPYTER_CONFIG_FILE
        if self.args.jupyter_config_file is not None:
            container_env["JUPYTER_CONFIG_FILE"] = self.args.jupyter_config_file

        # Init Airflow
        if self.args.init_airflow:
            container_env[INIT_AIRFLOW_ENV_VAR] = str(self.args.init_airflow)

        # Set the AIRFLOW_ENV
        if self.args.airflow_env is not None:
            container_env[AIRFLOW_ENV_ENV_VAR] = self.args.airflow_env

        # Set the AIRFLOW__CORE__DAGS_FOLDER
        if self.args.mount_workspace and self.args.use_workspace_for_airflow_dags:
            container_env[AIRFLOW_DAGS_FOLDER_ENV_VAR] = container_paths.workspace_root

        # Set the Airflow Executor
        container_env[AIRFLOW_EXECUTOR_ENV_VAR] = str(self.args.airflow_executor)

        # Airflow db connection
        airflow_db_user = self.get_airflow_db_user()
        airflow_db_password = self.get_airflow_db_password()
        airflow_db_schema = self.get_airflow_db_schema()
        airflow_db_host = self.get_airflow_db_host()
        airflow_db_port = self.get_airflow_db_port()
        airflow_db_driver = self.get_airflow_db_driver()
        if self.args.airflow_db_app is not None and isinstance(
            self.args.airflow_db_app, DbApp
        ):
            logger.debug(
                f"Reading db connection details from: {self.args.airflow_db_app.name}"
            )
            if airflow_db_user is None:
                airflow_db_user = self.args.airflow_db_app.get_db_user()
            if airflow_db_password is None:
                airflow_db_password = self.args.airflow_db_app.get_db_password()
            if airflow_db_schema is None:
                airflow_db_schema = self.args.airflow_db_app.get_db_schema()
            if airflow_db_host is None:
                airflow_db_host = self.args.airflow_db_app.get_db_host_docker()
            if airflow_db_port is None:
                airflow_db_port = str(self.args.airflow_db_app.get_db_port_docker())
            if airflow_db_driver is None:
                airflow_db_driver = self.args.airflow_db_app.get_db_driver()
        airflow_db_connection_url = f"{airflow_db_driver}://{airflow_db_user}:{airflow_db_password}@{airflow_db_host}:{airflow_db_port}/{airflow_db_schema}"

        # Set the AIRFLOW__DATABASE__SQL_ALCHEMY_CONN
        if "None" not in airflow_db_connection_url:
            # logger.debug(f"AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: {db_connection_url}")
            container_env[AIRFLOW_DB_CONN_URL_ENV_VAR] = airflow_db_connection_url

        # Airflow redis connection
        if self.args.airflow_executor == "CeleryExecutor":
            # Airflow celery result backend
            celery_result_backend_driver = (
                self.args.airflow_db_result_backend_driver or airflow_db_driver
            )
            celery_result_backend_url = f"{celery_result_backend_driver}://{airflow_db_user}:{airflow_db_password}@{airflow_db_host}:{airflow_db_port}/{airflow_db_schema}"
            # Set the AIRFLOW__CELERY__RESULT_BACKEND
            if "None" not in celery_result_backend_url:
                container_env[
                    "AIRFLOW__CELERY__RESULT_BACKEND"
                ] = celery_result_backend_url

            # Airflow celery broker url
            _airflow_redis_pass = self.get_airflow_redis_password()
            airflow_redis_password = (
                f"{_airflow_redis_pass}@" if _airflow_redis_pass else ""
            )
            airflow_redis_schema = self.get_airflow_redis_schema()
            airflow_redis_host = self.get_airflow_redis_host()
            airflow_redis_port = self.get_airflow_redis_port()
            airflow_redis_driver = self.get_airflow_redis_driver()
            if self.args.airflow_redis_app is not None and isinstance(
                self.args.airflow_redis_app, DbApp
            ):
                logger.debug(
                    f"Reading redis connection details from: {self.args.airflow_redis_app.name}"
                )
                if airflow_redis_password is None:
                    airflow_redis_password = (
                        self.args.airflow_redis_app.get_db_password()
                    )
                if airflow_redis_schema is None:
                    airflow_redis_schema = (
                        self.args.airflow_redis_app.get_db_schema() or "0"
                    )
                if airflow_redis_host is None:
                    airflow_redis_host = (
                        self.args.airflow_redis_app.get_db_host_docker()
                    )
                if airflow_redis_port is None:
                    airflow_redis_port = str(
                        self.args.airflow_redis_app.get_db_port_docker()
                    )
                if airflow_redis_driver is None:
                    airflow_redis_driver = self.args.airflow_redis_app.get_db_driver()

            # Set the AIRFLOW__CELERY__RESULT_BACKEND
            celery_broker_url = f"{airflow_redis_driver}://{airflow_redis_password}{airflow_redis_host}:{airflow_redis_port}/{airflow_redis_schema}"
            if "None" not in celery_broker_url:
                # logger.debug(f"AIRFLOW__CELERY__BROKER_URL: {celery_broker_url}")
                container_env["AIRFLOW__CELERY__BROKER_URL"] = celery_broker_url

        # Update the container env using env_file
        env_data_from_file = self.get_env_data()
        if env_data_from_file is not None:
            container_env.update(env_data_from_file)

        # Update the container env with user provided env, this overwrites any existing variables
        if self.args.env is not None and isinstance(self.args.env, dict):
            container_env.update(self.args.env)

        # Create a ConfigMap to set the container env variables which are not Secret
        container_env_cm = CreateConfigMap(
            cm_name=self.args.configmap_name or self.get_configmap_name(),
            app_name=app_name,
            namespace=ns_name,
            data=container_env,
            labels=common_labels,
        )
        config_maps.append(container_env_cm)

        # Create a Secret to set the container env variables which are Secret
        _secret_data = self.get_secret_data()
        if _secret_data is not None:
            container_env_secret = CreateSecret(
                secret_name=self.args.secret_name or self.get_secret_name(),
                app_name=app_name,
                string_data=_secret_data,
                namespace=ns_name,
                labels=common_labels,
            )
            secrets.append(container_env_secret)

        # Container Volumes
        # Add NodeSelectors to Pods in case we create az sensitive volumes
        pod_node_selector: Optional[Dict[str, str]] = self.args.pod_node_selector
        if self.args.create_volume:
            volume_name = self.args.volume_name
            if volume_name is None:
                if workspace_name is not None:
                    volume_name = get_default_volume_name(
                        f"{app_name}-{workspace_name}"
                    )
                else:
                    volume_name = get_default_volume_name(app_name)

            if self.args.volume_type == JupyterVolumeType.AwsEbs:
                if (
                    self.args.ebs_volume_id is not None
                    or self.args.ebs_volume is not None
                ):
                    # To use an EbsVolume as the volume_type we:
                    # 1. Need the volume_id
                    # 2. Need to make sure pods are scheduled in the
                    #       same region/az as the volume

                    # For the volume_id we can either:
                    # 1. Use self.args.ebs_volume_id
                    # 2. Derive it from the self.args.ebs_volume
                    ebs_volume_id = self.args.ebs_volume_id

                    # For the aws_region/az:
                    # 1. Use self.args.ebs_volume_region
                    # 2. Derive it from self.args.ebs_volume
                    # 3. Derive it from the PhidataAppArgs
                    ebs_volume_region = self.args.ebs_volume_region
                    ebs_volume_az = self.args.ebs_volume_az

                    # Derive the aws_region from self.args.ebs_volume if needed
                    if ebs_volume_region is None and self.args.ebs_volume is not None:
                        # Note: this will use the `$AWS_REGION` env var if set
                        _aws_region_from_ebs_volume = (
                            self.args.ebs_volume.get_aws_region()
                        )
                        if _aws_region_from_ebs_volume is not None:
                            ebs_volume_region = _aws_region_from_ebs_volume

                    # Derive the aws_region from the PhidataAppArgs if needed
                    if ebs_volume_region is None:
                        ebs_volume_region = self.aws_region

                    # Derive the availability_zone from self.args.ebs_volume if needed
                    if ebs_volume_az is None and self.args.ebs_volume is not None:
                        ebs_volume_az = self.args.ebs_volume.availability_zone

                    logger.debug(f"ebs_volume_region: {ebs_volume_region}")
                    logger.debug(f"ebs_volume_az: {ebs_volume_az}")

                    # Derive ebs_volume_id from self.args.ebs_volume if needed
                    if ebs_volume_id is None and self.args.ebs_volume is not None:
                        ebs_volume_id = self.args.ebs_volume.get_volume_id(
                            aws_region=ebs_volume_region,
                            aws_profile=self.aws_profile,
                        )

                    logger.debug(f"ebs_volume_id: {ebs_volume_id}")
                    if ebs_volume_id is None:
                        logger.error("Could not find volume_id for EbsVolume")
                        return None

                    ebs_volume = CreateVolume(
                        volume_name=volume_name,
                        app_name=app_name,
                        mount_path=self.args.volume_container_path,
                        volume_type=VolumeType.AWS_EBS,
                        aws_ebs=AwsElasticBlockStoreVolumeSource(
                            volume_id=ebs_volume_id,
                        ),
                    )
                    volumes.append(ebs_volume)

                    # VERY IMPORTANT: pods should be scheduled in the same region/az as the volume
                    # To do this, we add NodeSelectors to Pods
                    if self.args.schedule_pods_in_ebs_topology:
                        if pod_node_selector is None:
                            pod_node_selector = {}

                        # Add NodeSelectors to Pods, so they are scheduled in the same
                        # region and zone as the ebs_volume
                        # https://kubernetes.io/docs/reference/labels-annotations-taints/#topologykubernetesiozone
                        if ebs_volume_region is not None:
                            pod_node_selector[
                                "topology.kubernetes.io/region"
                            ] = ebs_volume_region

                        if ebs_volume_az is not None:
                            pod_node_selector[
                                "topology.kubernetes.io/zone"
                            ] = ebs_volume_az
                else:
                    logger.error("JupyterLab: ebs_volume not provided")
                    return None

            elif self.args.volume_type == JupyterVolumeType.EmptyDir:
                empty_dir_volume = CreateVolume(
                    volume_name=volume_name,
                    app_name=app_name,
                    mount_path=self.args.volume_container_path,
                    volume_type=VolumeType.EMPTY_DIR,
                )
                volumes.append(empty_dir_volume)

            elif self.args.volume_type == JupyterVolumeType.HostPath:
                if self.args.volume_host_path is not None:
                    volume_host_path_str = str(self.args.volume_host_path)
                    host_path_volume = CreateVolume(
                        volume_name=volume_name,
                        app_name=app_name,
                        mount_path=self.args.volume_container_path,
                        volume_type=VolumeType.HOST_PATH,
                        host_path=HostPathVolumeSource(
                            path=volume_host_path_str,
                        ),
                    )
                    volumes.append(host_path_volume)
                else:
                    logger.error("PostgresDb: volume_host_path not provided")
                    return None

        if self.args.mount_workspace:
            workspace_volume_name = self.args.workspace_volume_name
            if workspace_volume_name is None:
                if workspace_name is not None:
                    workspace_volume_name = get_default_volume_name(
                        f"jupyter-{workspace_name}-ws"
                    )
                else:
                    workspace_volume_name = get_default_volume_name("jupyter-ws")

            # Mount workspace volume as EmptyDir then use git-sync to sync the workspace from github
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

        # Create the ports to open
        if self.args.open_container_port:
            container_port = CreatePort(
                name=self.args.container_port_name,
                container_port=self.args.container_port,
                service_port=self.args.service_port,
                target_port=self.args.service_target_port
                or self.args.container_port_name,
            )
            ports.append(container_port)

        # if open_app_port = True
        if self.args.open_app_port:
            app_port = CreatePort(
                name=self.args.app_port_name,
                container_port=self.args.app_port,
                service_port=self.get_app_service_port(),
                node_port=self.args.app_node_port,
                target_port=self.args.app_target_port or self.args.app_port_name,
            )
            ports.append(app_port)

        container_labels: Dict[str, Any] = common_labels or {}
        if self.args.container_labels is not None and isinstance(
            self.args.container_labels, dict
        ):
            container_labels.update(self.args.container_labels)

        # Equivalent to docker images CMD
        container_args: List[str]
        if isinstance(self.args.command, str):
            container_args = self.args.command.split(" ")
        else:
            container_args = self.args.command

        if self.args.jupyter_config_file is not None:
            container_args.append(f"--config={str(self.args.jupyter_config_file)}")

        if self.args.notebook_dir is None:
            container_args.append("--notebook-dir=/mnt")
        else:
            container_args.append(f"--notebook-dir={str(self.args.notebook_dir)}")

        # container_args.append("--ip=0.0.0.0")

        # Create the JupyterLab container
        jupyterlab_container = CreateContainer(
            container_name=self.get_container_name(),
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
        containers.insert(0, jupyterlab_container)

        # Set default container for kubectl commands
        # https://kubernetes.io/docs/reference/labels-annotations-taints/#kubectl-kubernetes-io-default-container
        pod_annotations = {
            "kubectl.kubernetes.io/default-container": jupyterlab_container.container_name
        }
        if self.args.pod_annotations is not None and isinstance(
            self.args.pod_annotations, dict
        ):
            pod_annotations.update(self.args.pod_annotations)

        deploy_labels: Dict[str, Any] = common_labels or {}
        if self.args.deploy_labels is not None and isinstance(
            self.args.deploy_labels, dict
        ):
            deploy_labels.update(self.args.deploy_labels)

        # If using EbsVolume, restart the deployment on update
        recreate_deployment_on_update = (
            True
            if (
                self.args.create_volume
                and self.args.volume_type == JupyterVolumeType.AwsEbs
            )
            else False
        )

        # Create the deployment
        jupyterlab_deployment = CreateDeployment(
            deploy_name=self.get_deploy_name(),
            pod_name=self.get_pod_name(),
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
        deployments.append(jupyterlab_deployment)

        # Create the services
        if self.args.create_service:
            service_labels: Dict[str, Any] = common_labels or {}
            if self.args.service_labels is not None and isinstance(
                self.args.service_labels, dict
            ):
                service_labels.update(self.args.service_labels)

            _service = CreateService(
                service_name=self.get_service_name(),
                app_name=app_name,
                namespace=ns_name,
                service_account_name=sa_name,
                service_type=self.args.service_type,
                deployment=jupyterlab_deployment,
                ports=ports if len(ports) > 0 else None,
                labels=service_labels,
            )
            services.append(_service)

        if self.args.create_app_service:
            app_svc_labels: Dict[str, Any] = common_labels or {}
            if self.args.app_svc_labels is not None and isinstance(
                self.args.app_svc_labels, dict
            ):
                app_svc_labels.update(self.args.app_svc_labels)

            app_service = CreateService(
                service_name=self.get_app_service_name(),
                app_name=app_name,
                namespace=ns_name,
                service_account_name=sa_name,
                service_type=self.args.app_svc_type,
                deployment=jupyterlab_deployment,
                ports=ports if len(ports) > 0 else None,
                labels=app_svc_labels,
            )
            services.append(app_service)

        # Create the K8sResourceGroup
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

    def init_k8s_resource_groups(self, k8s_build_context: Any) -> None:
        k8s_rg = self.get_k8s_rg(k8s_build_context)
        if k8s_rg is not None:
            from collections import OrderedDict

            if self.k8s_resource_groups is None:
                self.k8s_resource_groups = OrderedDict()
            self.k8s_resource_groups[k8s_rg.name] = k8s_rg

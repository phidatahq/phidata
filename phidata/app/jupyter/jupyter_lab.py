from collections import OrderedDict
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from typing_extensions import Literal

from phidata.app import PhidataApp, PhidataAppArgs
from phidata.constants import (
    SCRIPTS_DIR_ENV_VAR,
    STORAGE_DIR_ENV_VAR,
    META_DIR_ENV_VAR,
    PRODUCTS_DIR_ENV_VAR,
    NOTEBOOKS_DIR_ENV_VAR,
    WORKSPACE_CONFIG_DIR_ENV_VAR,
    PHIDATA_RUNTIME_ENV_VAR,
)
from phidata.infra.docker.resource.group import (
    DockerResourceGroup,
    DockerBuildContext,
    DockerContainer,
    DockerNetwork,
)
from phidata.infra.k8s.create.apps.v1.deployment import RestartPolicy
from phidata.infra.k8s.create.core.v1.service import ServiceType
from phidata.infra.k8s.create.core.v1.container import CreateContainer, ImagePullPolicy
from phidata.infra.k8s.create.core.v1.persistent_volume import (
    ClaimRef,
    NFSVolumeSource,
)
from phidata.infra.k8s.create.rbac_authorization_k8s_io.v1.cluster_role import (
    PolicyRule,
)
from phidata.infra.k8s.create.core.v1.volume import (
    CreateVolume,
    HostPathVolumeSource,
    VolumeType,
    PersistentVolumeClaimVolumeSource,
)
from phidata.infra.k8s.create.common.port import CreatePort
from phidata.infra.k8s.create.group import (
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
from phidata.infra.k8s.enums.pv import PVAccessMode
from phidata.infra.k8s.resource.group import (
    K8sResourceGroup,
    K8sBuildContext,
)
from phidata.utils.common import (
    get_image_str,
    get_default_ns_name,
    get_default_container_name,
    get_default_configmap_name,
    get_default_secret_name,
    get_default_service_name,
    get_default_deploy_name,
    get_default_pod_name,
    get_default_volume_name,
    get_default_cr_name,
    get_default_crb_name,
    get_default_sa_name,
)
from phidata.utils.enums import ExtendedEnum
from phidata.utils.log import logger


class JupyterLabArgs(PhidataAppArgs):
    name: str = "jupyterlab"
    version: str = "1"
    enabled: bool = True

    # Image args
    image_name: str = "phidata/jupyterlab"
    image_tag: str = "3.4.3"
    entrypoint: Optional[Union[str, List]] = None
    command: Union[str, List] = "jupyter lab"

    # Install python dependencies using a requirements.txt file
    # Sets the REQUIREMENTS_FILE_PATH env var to requirements_file_path
    install_requirements: bool = False
    # Path to the requirements.txt file relative to the workspace_root
    requirements_file_path: str = "workspace/jupyter/requirements.txt"

    # Configure the jupyter container
    container_name: Optional[str] = None
    # Path to JUPYTER_CONFIG_FILE relative to the workspace_root
    # Used to set the JUPYTER_CONFIG_FILE env var
    # This value is also appended to the command using `--config`
    jupyter_config_file: Optional[str] = None
    # Set the workspace_root_container_path as `--notebook-dir`
    use_workspace_as_notebook_dir: Optional[bool] = False
    # Overwrite the PYTHONPATH env var, which is usually set
    # to workspace_root_contaier_path
    python_path: Optional[str] = None
    # Add labels to the container
    container_labels: Optional[Dict[str, Any]] = None

    # Docker configuration
    # NOTE: Only available for Docker
    # Run container in the background and return a Container object.
    container_detach: bool = True
    # Enable auto-removal of the container on daemon side when the container’s process exits.
    container_auto_remove: bool = True
    # Remove the container when it has finished running. Default: False.
    container_remove: bool = True
    # Username or UID to run commands as inside the container.
    container_user: Optional[Union[str, int]] = None
    # Keep STDIN open even if not attached.
    container_stdin_open: bool = True
    container_tty: bool = True
    # Specify a test to perform to check that the container is healthy.
    container_healthcheck: Optional[Dict[str, Any]] = None
    # Optional hostname for the container.
    container_hostname: Optional[str] = None
    # Platform in the format os[/arch[/variant]].
    container_platform: str = "linux/amd64"
    # Path to the working directory.
    container_working_dir: Optional[str] = None
    # Restart the container when it exits. Configured as a dictionary with keys:
    # Name: One of on-failure, or always.
    # MaximumRetryCount: Number of times to restart the container on failure.
    # For example: {"Name": "on-failure", "MaximumRetryCount": 5}
    container_restart_policy_docker: Optional[Dict[str, Any]] = None
    # Add volumes to DockerContainer
    # container_volumes is a dictionary which adds the volumes to mount
    # inside the container. The key is either the host path or a volume name,
    # and the value is a dictionary with 2 keys:
    #   bind - The path to mount the volume inside the container
    #   mode - Either rw to mount the volume read/write, or ro to mount it read-only.
    # For example:
    # {
    #   '/home/user1/': {'bind': '/mnt/vol2', 'mode': 'rw'},
    #   '/var/www': {'bind': '/mnt/vol1', 'mode': 'ro'}
    # }
    container_volumes_docker: Optional[Dict[str, dict]] = None
    # Add ports to DockerContainer
    # The keys of the dictionary are the ports to bind inside the container,
    # either as an integer or a string in the form port/protocol, where the protocol is either tcp, udp.
    # The values of the dictionary are the corresponding ports to open on the host, which can be either:
    #   - The port number, as an integer.
    #       For example, {'2222/tcp': 3333} will expose port 2222 inside the container as port 3333 on the host.
    #   - None, to assign a random host port. For example, {'2222/tcp': None}.
    #   - A tuple of (address, port) if you want to specify the host interface.
    #       For example, {'1111/tcp': ('127.0.0.1', 1111)}.
    #   - A list of integers, if you want to bind multiple host ports to a single container port.
    #       For example, {'1111/tcp': [1234, 4567]}.
    container_ports_docker: Optional[Dict[str, Any]] = None

    # K8s configuration
    # NOTE: Only available for Kubernetes
    image_pull_policy: ImagePullPolicy = ImagePullPolicy.IF_NOT_PRESENT

    # Container ports
    # Open a container port if open_container_port=True
    open_container_port: bool = False
    # Port number on the container
    container_port: int = 8000
    # Port name: Only used by the K8sContainer
    container_port_name: str = "http"
    # Host port: Only used by the DockerContainer
    container_host_port: int = 8000

    # Open the app port if open_app_port=True
    open_app_port: bool = True
    # App port number on the container
    # Set the SUPERSET_PORT env var
    app_port: int = 8888
    # Only used by the K8sContainer
    app_port_name: str = "app"
    # Only used by the DockerContainer
    app_host_port: int = 8888

    # Container env
    # Add env variables to container env
    env: Optional[Dict[str, str]] = None
    # Read env variables from a file in yaml format
    env_file: Optional[Path] = None
    # Configure the ConfigMap name used for env variables that are not Secret
    config_map_name: Optional[str] = None

    # Container secrets
    # Add secret variables to container env
    secrets: Optional[Dict[str, str]] = None
    # Read secret variables from a file in yaml format
    secrets_file: Optional[Path] = None
    # Read secret variables from AWS Secrets Manager
    aws_secret: Optional[Any] = None
    # Configure the Secret name used for env variables that are Secret
    secret_name: Optional[str] = None

    # Container volumes
    # Configure workspace volume
    # Mount the workspace directory on the container
    mount_workspace: bool = False
    workspace_volume_name: Optional[str] = None
    # Path to mount the workspace volume under
    # This is the parent directory for the workspace on the container
    # i.e. the ws is mounted as a subdir in this dir
    # eg: if ws name is: idata, workspace_root would be: /mnt/workspaces/idata
    workspace_mount_container_path: str = "/mnt/workspaces"
    # NOTE: On DockerContainers the local workspace_root_path is mounted under workspace_mount_container_path
    # because we assume that DockerContainers are running locally on the user's machine
    # On K8sContainers, we load the workspace_dir from git using a git-sync sidecar container
    create_git_sync_sidecar: bool = True
    create_git_sync_init_container: bool = True
    git_sync_repo: Optional[str] = None
    git_sync_branch: Optional[str] = None
    git_sync_wait: int = 1
    # When running k8s locally, we can mount the workspace using host path as well.
    k8s_mount_local_workspace = False

    # Configure resources volume - only on docker
    # Jupyter resources directory relative to the workspace_root
    # This dir is mounted to the `/usr/local/jupyter` directory on the container
    mount_resources: bool = False
    resources_dir: str = "workspace/jupyter"
    resources_dir_container_path: str = "/usr/local/jupyter"
    resources_volume_name: Optional[str] = None

    # Configure the deployment
    deploy_name: Optional[str] = None
    pod_name: Optional[str] = None
    replicas: int = 1
    pod_annotations: Optional[Dict[str, str]] = None
    pod_node_selector: Optional[Dict[str, str]] = None
    deploy_restart_policy: RestartPolicy = RestartPolicy.ALWAYS
    termination_grace_period_seconds: Optional[int] = None
    # Add deployment labels
    deploy_labels: Optional[Dict[str, Any]] = None
    # Determine how to spread the deployment across a topology
    # Key to spread the pods across
    topology_spread_key: Optional[str] = None
    # The degree to which pods may be unevenly distributed
    topology_spread_max_skew: Optional[int] = None
    # How to deal with a pod if it doesn't satisfy the spread constraint.
    topology_spread_when_unsatisfiable: Optional[
        Literal["DoNotSchedule", "ScheduleAnyway"]
    ] = None

    # Configure the app service
    create_app_svc: bool = False
    app_svc_name: Optional[str] = None
    app_svc_type: Optional[ServiceType] = None
    # The port that will be exposed by the service.
    app_svc_port: int = 8888
    # The node_port that will be exposed by the service if app_svc_type = ServiceType.NODE_PORT
    app_node_port: Optional[int] = None
    # The app_target_port is the port to access on the pods targeted by the service.
    # It can be the port number or port name on the pod.
    app_target_port: Optional[Union[str, int]] = None
    # Extra ports exposed by the app service
    app_svc_ports: Optional[List[CreatePort]] = None
    # Add labels to app service
    app_svc_labels: Optional[Dict[str, Any]] = None
    # Add annotations to app service
    app_svc_annotations: Optional[Dict[str, str]] = None
    # If ServiceType == LoadBalancer
    app_svc_health_check_node_port: Optional[int] = None
    app_svc_internal_taffic_policy: Optional[str] = None
    app_svc_load_balancer_class: Optional[str] = None
    app_svc_load_balancer_ip: Optional[str] = None
    app_svc_load_balancer_source_ranges: Optional[List[str]] = None
    app_svc_allocate_load_balancer_node_ports: Optional[bool] = None

    # Configure K8s rbac: use a separate Namespace, ServiceAccount,
    # ClusterRole & ClusterRoleBinding
    use_rbac: bool = False
    # Create a Namespace with name ns_name & default values
    ns_name: Optional[str] = None
    # Provide the full Namespace definition
    namespace: Optional[CreateNamespace] = None
    # Create a ServiceAccount with name sa_name & default values
    sa_name: Optional[str] = None
    # Provide the full ServiceAccount definition
    service_account: Optional[CreateServiceAccount] = None
    # Create a ClusterRole with name sa_name & default values
    cr_name: Optional[str] = None
    # Provide the full ClusterRole definition
    cluster_role: Optional[CreateClusterRole] = None
    # Create a ClusterRoleBinding with name sa_name & default values
    crb_name: Optional[str] = None
    # Provide the full ClusterRoleBinding definition
    cluster_role_binding: Optional[CreateClusterRoleBinding] = None

    # Other args
    load_examples: bool = False
    print_env_on_load: bool = True

    # Add extra Kubernetes resources
    extra_secrets: Optional[List[CreateSecret]] = None
    extra_config_maps: Optional[List[CreateConfigMap]] = None
    extra_storage_classes: Optional[List[CreateStorageClass]] = None
    extra_services: Optional[List[CreateService]] = None
    extra_deployments: Optional[List[CreateDeployment]] = None
    extra_custom_objects: Optional[List[CreateCustomObject]] = None
    extra_crds: Optional[List[CreateCustomResourceDefinition]] = None
    extra_pvs: Optional[List[CreatePersistentVolume]] = None
    extra_pvcs: Optional[List[CreatePVC]] = None
    extra_containers: Optional[List[CreateContainer]] = None
    extra_init_containers: Optional[List[CreateContainer]] = None
    extra_ports: Optional[List[CreatePort]] = None
    extra_volumes: Optional[List[CreateVolume]] = None


class JupyterLab(PhidataApp):
    def __init__(
        self,
        name: str = "jupyterlab",
        version: str = "1",
        enabled: bool = True,
        # Image args,
        image_name: str = "phidata/jupyterlab",
        image_tag: str = "3.4.3",
        entrypoint: Optional[Union[str, List]] = None,
        command: Union[str, List] = "jupyter lab",
        # Install python dependencies using a requirements.txt file,
        # Sets the REQUIREMENTS_FILE_PATH env var to requirements_file_path,
        install_requirements: bool = False,
        # Path to the requirements.txt file relative to the workspace_root,
        requirements_file_path: str = "workspace/jupyter/requirements.txt",
        # Configure the jupyter container,
        container_name: Optional[str] = None,
        # Path to JUPYTER_CONFIG_FILE relative to the workspace_root,
        # Used to set the JUPYTER_CONFIG_FILE env var,
        # This value is also appended to the command using `--config`,
        jupyter_config_file: Optional[str] = None,
        # Set the workspace_root_container_path as `--notebook-dir`,
        use_workspace_as_notebook_dir: Optional[bool] = False,
        # Overwrite the PYTHONPATH env var, which is usually set,
        # to workspace_root_contaier_path,
        python_path: Optional[str] = None,
        # Add labels to the container,
        container_labels: Optional[Dict[str, Any]] = None,
        # Docker configuration,
        # NOTE: Only available for Docker,
        # Run container in the background and return a Container object.,
        container_detach: bool = True,
        # Enable auto-removal of the container on daemon side when the container’s process exits.,
        container_auto_remove: bool = True,
        # Remove the container when it has finished running. Default: False.,
        container_remove: bool = True,
        # Username or UID to run commands as inside the container.,
        container_user: Optional[Union[str, int]] = None,
        # Keep STDIN open even if not attached.,
        container_stdin_open: bool = True,
        container_tty: bool = True,
        # Specify a test to perform to check that the container is healthy.,
        container_healthcheck: Optional[Dict[str, Any]] = None,
        # Optional hostname for the container.,
        container_hostname: Optional[str] = None,
        # Platform in the format os[/arch[/variant]].,
        container_platform: str = "linux/amd64",
        # Path to the working directory.,
        container_working_dir: Optional[str] = None,
        # Restart the container when it exits. Configured as a dictionary with keys:,
        # Name: One of on-failure, or always.,
        # MaximumRetryCount: Number of times to restart the container on failure.,
        # For example: {"Name": "on-failure", "MaximumRetryCount": 5},
        container_restart_policy_docker: Optional[Dict[str, Any]] = None,
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
        container_volumes_docker: Optional[Dict[str, dict]] = None,
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
        container_ports_docker: Optional[Dict[str, Any]] = None,
        # K8s configuration,
        # NOTE: Only available for Kubernetes,
        image_pull_policy: ImagePullPolicy = ImagePullPolicy.IF_NOT_PRESENT,
        # Container ports,
        # Open a container port if open_container_port=True,
        open_container_port: bool = False,
        # Port number on the container,
        container_port: int = 8000,
        # Port name: Only used by the K8sContainer,
        container_port_name: str = "http",
        # Host port: Only used by the DockerContainer,
        container_host_port: int = 8000,
        # Open the app port if open_app_port=True,
        open_app_port: bool = True,
        # App port number on the container,
        # Set the SUPERSET_PORT env var,
        app_port: int = 8888,
        # Only used by the K8sContainer,
        app_port_name: str = "app",
        # Only used by the DockerContainer,
        app_host_port: int = 8888,
        # Container env,
        # Add env variables to container env,
        env: Optional[Dict[str, str]] = None,
        # Read env variables from a file in yaml format,
        env_file: Optional[Path] = None,
        # Configure the ConfigMap name used for env variables that are not Secret,
        config_map_name: Optional[str] = None,
        # Container secrets,
        # Add secret variables to container env,
        secrets: Optional[Dict[str, str]] = None,
        # Read secret variables from a file in yaml format,
        secrets_file: Optional[Path] = None,
        # Read secret variables from AWS Secrets Manager,
        aws_secret: Optional[Any] = None,
        # Configure the Secret name used for env variables that are Secret,
        secret_name: Optional[str] = None,
        # Container volumes,
        # Configure workspace volume,
        # Mount the workspace directory on the container,
        mount_workspace: bool = False,
        workspace_volume_name: Optional[str] = None,
        # Path to mount the workspace volume under,
        # This is the parent directory for the workspace on the container,
        # i.e. the ws is mounted as a subdir in this dir,
        # eg: if ws name is: idata, workspace_root would be: /mnt/workspaces/idata,
        workspace_mount_container_path: str = "/mnt/workspaces",
        # NOTE: On DockerContainers the local workspace_root_path is mounted under workspace_mount_container_path,
        # because we assume that DockerContainers are running locally on the user's machine,
        # On K8sContainers, we load the workspace_dir from git using a git-sync sidecar container,
        create_git_sync_sidecar: bool = True,
        create_git_sync_init_container: bool = True,
        git_sync_repo: Optional[str] = None,
        git_sync_branch: Optional[str] = None,
        git_sync_wait: int = 1,
        # When running k8s locally, we can mount the workspace using host path as well.,
        k8s_mount_local_workspace=False,
        # Configure resources volume - only on docker,
        # Jupyter resources directory relative to the workspace_root,
        # This dir is mounted to the `/usr/local/jupyter` directory on the container,
        mount_resources: bool = False,
        resources_dir: str = "workspace/jupyter",
        resources_dir_container_path: str = "/usr/local/jupyter",
        resources_volume_name: Optional[str] = None,
        # Configure the deployment,
        deploy_name: Optional[str] = None,
        pod_name: Optional[str] = None,
        replicas: int = 1,
        pod_annotations: Optional[Dict[str, str]] = None,
        pod_node_selector: Optional[Dict[str, str]] = None,
        deploy_restart_policy: RestartPolicy = RestartPolicy.ALWAYS,
        termination_grace_period_seconds: Optional[int] = None,
        # Add deployment labels,
        deploy_labels: Optional[Dict[str, Any]] = None,
        # Determine how to spread the deployment across a topology,
        # Key to spread the pods across,
        topology_spread_key: Optional[str] = None,
        # The degree to which pods may be unevenly distributed,
        topology_spread_max_skew: Optional[int] = None,
        # How to deal with a pod if it doesn't satisfy the spread constraint.,
        topology_spread_when_unsatisfiable: Optional[
            Literal["DoNotSchedule", "ScheduleAnyway"]
        ] = None,
        # Configure the app service,
        create_app_svc: bool = False,
        app_svc_name: Optional[str] = None,
        app_svc_type: Optional[ServiceType] = None,
        # The port that will be exposed by the service.,
        app_svc_port: int = 8888,
        # The node_port that will be exposed by the service if app_svc_type = ServiceType.NODE_PORT,
        app_node_port: Optional[int] = None,
        # The app_target_port is the port to access on the pods targeted by the service.,
        # It can be the port number or port name on the pod.,
        app_target_port: Optional[Union[str, int]] = None,
        # Extra ports exposed by the app service,
        app_svc_ports: Optional[List[CreatePort]] = None,
        # Add labels to app service,
        app_svc_labels: Optional[Dict[str, Any]] = None,
        # Add annotations to app service,
        app_svc_annotations: Optional[Dict[str, str]] = None,
        # If ServiceType == LoadBalancer,
        app_svc_health_check_node_port: Optional[int] = None,
        app_svc_internal_taffic_policy: Optional[str] = None,
        app_svc_load_balancer_class: Optional[str] = None,
        app_svc_load_balancer_ip: Optional[str] = None,
        app_svc_load_balancer_source_ranges: Optional[List[str]] = None,
        app_svc_allocate_load_balancer_node_ports: Optional[bool] = None,
        # Configure K8s rbac: use a separate Namespace, ServiceAccount,,
        # ClusterRole & ClusterRoleBinding,
        use_rbac: bool = False,
        # Create a Namespace with name ns_name & default values,
        ns_name: Optional[str] = None,
        # Provide the full Namespace definition,
        namespace: Optional[CreateNamespace] = None,
        # Create a ServiceAccount with name sa_name & default values,
        sa_name: Optional[str] = None,
        # Provide the full ServiceAccount definition,
        service_account: Optional[CreateServiceAccount] = None,
        # Create a ClusterRole with name sa_name & default values,
        cr_name: Optional[str] = None,
        # Provide the full ClusterRole definition,
        cluster_role: Optional[CreateClusterRole] = None,
        # Create a ClusterRoleBinding with name sa_name & default values,
        crb_name: Optional[str] = None,
        # Provide the full ClusterRoleBinding definition,
        cluster_role_binding: Optional[CreateClusterRoleBinding] = None,
        # Other args,
        load_examples: bool = False,
        print_env_on_load: bool = True,
        # Add extra Kubernetes resources,
        extra_secrets: Optional[List[CreateSecret]] = None,
        extra_config_maps: Optional[List[CreateConfigMap]] = None,
        extra_storage_classes: Optional[List[CreateStorageClass]] = None,
        extra_services: Optional[List[CreateService]] = None,
        extra_deployments: Optional[List[CreateDeployment]] = None,
        extra_custom_objects: Optional[List[CreateCustomObject]] = None,
        extra_crds: Optional[List[CreateCustomResourceDefinition]] = None,
        extra_pvs: Optional[List[CreatePersistentVolume]] = None,
        extra_pvcs: Optional[List[CreatePVC]] = None,
        extra_containers: Optional[List[CreateContainer]] = None,
        extra_init_containers: Optional[List[CreateContainer]] = None,
        extra_ports: Optional[List[CreatePort]] = None,
        extra_volumes: Optional[List[CreateVolume]] = None,
        # If True, use cached resources
        # i.e. skip resource creation/deletion if active resources with the same name exist.
        use_cache: bool = True,
        **extra_kwargs,
    ):
        super().__init__()

        # Cache env_data & secret_data
        self.env_data: Optional[Dict[str, Any]] = None
        self.secret_data: Optional[Dict[str, Any]] = None

        try:
            self.args: JupyterLabArgs = JupyterLabArgs(
                name=name,
                version=version,
                enabled=enabled,
                image_name=image_name,
                image_tag=image_tag,
                entrypoint=entrypoint,
                command=command,
                install_requirements=install_requirements,
                requirements_file_path=requirements_file_path,
                container_name=container_name,
                jupyter_config_file=jupyter_config_file,
                use_workspace_as_notebook_dir=use_workspace_as_notebook_dir,
                python_path=python_path,
                container_labels=container_labels,
                container_detach=container_detach,
                container_auto_remove=container_auto_remove,
                container_remove=container_remove,
                container_user=container_user,
                container_stdin_open=container_stdin_open,
                container_tty=container_tty,
                container_healthcheck=container_healthcheck,
                container_hostname=container_hostname,
                container_platform=container_platform,
                container_working_dir=container_working_dir,
                container_restart_policy_docker=container_restart_policy_docker,
                container_volumes_docker=container_volumes_docker,
                container_ports_docker=container_ports_docker,
                image_pull_policy=image_pull_policy,
                open_container_port=open_container_port,
                container_port=container_port,
                container_port_name=container_port_name,
                container_host_port=container_host_port,
                open_app_port=open_app_port,
                app_port=app_port,
                app_port_name=app_port_name,
                app_host_port=app_host_port,
                env=env,
                env_file=env_file,
                config_map_name=config_map_name,
                secrets=secrets,
                secrets_file=secrets_file,
                aws_secret=aws_secret,
                secret_name=secret_name,
                mount_workspace=mount_workspace,
                workspace_volume_name=workspace_volume_name,
                workspace_mount_container_path=workspace_mount_container_path,
                create_git_sync_sidecar=create_git_sync_sidecar,
                create_git_sync_init_container=create_git_sync_init_container,
                git_sync_repo=git_sync_repo,
                git_sync_branch=git_sync_branch,
                git_sync_wait=git_sync_wait,
                k8s_mount_local_workspace=k8s_mount_local_workspace,
                mount_resources=mount_resources,
                resources_dir=resources_dir,
                resources_dir_container_path=resources_dir_container_path,
                resources_volume_name=resources_volume_name,
                deploy_name=deploy_name,
                pod_name=pod_name,
                replicas=replicas,
                pod_annotations=pod_annotations,
                pod_node_selector=pod_node_selector,
                deploy_restart_policy=deploy_restart_policy,
                termination_grace_period_seconds=termination_grace_period_seconds,
                deploy_labels=deploy_labels,
                topology_spread_key=topology_spread_key,
                topology_spread_max_skew=topology_spread_max_skew,
                topology_spread_when_unsatisfiable=topology_spread_when_unsatisfiable,
                create_app_svc=create_app_svc,
                app_svc_name=app_svc_name,
                app_svc_type=app_svc_type,
                app_svc_port=app_svc_port,
                app_node_port=app_node_port,
                app_target_port=app_target_port,
                app_svc_ports=app_svc_ports,
                app_svc_labels=app_svc_labels,
                app_svc_annotations=app_svc_annotations,
                app_svc_health_check_node_port=app_svc_health_check_node_port,
                app_svc_internal_taffic_policy=app_svc_internal_taffic_policy,
                app_svc_load_balancer_class=app_svc_load_balancer_class,
                app_svc_load_balancer_ip=app_svc_load_balancer_ip,
                app_svc_load_balancer_source_ranges=app_svc_load_balancer_source_ranges,
                app_svc_allocate_load_balancer_node_ports=app_svc_allocate_load_balancer_node_ports,
                use_rbac=use_rbac,
                ns_name=ns_name,
                namespace=namespace,
                sa_name=sa_name,
                service_account=service_account,
                cr_name=cr_name,
                cluster_role=cluster_role,
                crb_name=crb_name,
                cluster_role_binding=cluster_role_binding,
                load_examples=load_examples,
                print_env_on_load=print_env_on_load,
                extra_secrets=extra_secrets,
                extra_config_maps=extra_config_maps,
                extra_storage_classes=extra_storage_classes,
                extra_services=extra_services,
                extra_deployments=extra_deployments,
                extra_custom_objects=extra_custom_objects,
                extra_crds=extra_crds,
                extra_pvs=extra_pvs,
                extra_pvcs=extra_pvcs,
                extra_containers=extra_containers,
                extra_init_containers=extra_init_containers,
                extra_ports=extra_ports,
                extra_volumes=extra_volumes,
                use_cache=use_cache,
                extra_kwargs=extra_kwargs,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    def get_container_name(self) -> str:
        return self.args.container_name or get_default_container_name(self.args.name)

    def get_app_service_name(self) -> str:
        return self.args.app_svc_name or get_default_service_name(self.args.name)

    def get_app_service_port(self) -> int:
        return self.args.app_svc_port

    def get_env_data(self) -> Optional[Dict[str, str]]:
        if self.env_data is None:
            self.env_data = self.read_yaml_file(file_path=self.args.env_file)
        return self.env_data

    def get_secret_data(self) -> Optional[Dict[str, str]]:
        if self.secret_data is None:
            self.secret_data = self.read_yaml_file(file_path=self.args.secrets_file)
        return self.secret_data

    ######################################################
    ## Docker Resources
    ######################################################

    def get_docker_rg(
        self, docker_build_context: DockerBuildContext
    ) -> Optional[DockerResourceGroup]:

        app_name = self.args.name
        logger.debug(f"Building {app_name} DockerResourceGroup")

        # Workspace paths
        if self.workspace_root_path is None:
            logger.error("Invalid workspace_root_path")
            return None
        workspace_name = self.workspace_root_path.stem
        workspace_root_container_path = Path(
            self.args.workspace_mount_container_path
        ).joinpath(workspace_name)
        requirements_file_container_path = workspace_root_container_path.joinpath(
            self.args.requirements_file_path
        )
        scripts_dir_container_path = (
            workspace_root_container_path.joinpath(self.scripts_dir)
            if self.scripts_dir
            else None
        )
        storage_dir_container_path = (
            workspace_root_container_path.joinpath(self.storage_dir)
            if self.storage_dir
            else None
        )
        meta_dir_container_path = (
            workspace_root_container_path.joinpath(self.meta_dir)
            if self.meta_dir
            else None
        )
        products_dir_container_path = (
            workspace_root_container_path.joinpath(self.products_dir)
            if self.products_dir
            else None
        )
        notebooks_dir_container_path = (
            workspace_root_container_path.joinpath(self.notebooks_dir)
            if self.notebooks_dir
            else None
        )
        workspace_config_dir_container_path = (
            workspace_root_container_path.joinpath(self.workspace_config_dir)
            if self.workspace_config_dir
            else None
        )

        # Container pythonpath
        python_path = (
            self.args.python_path
            or f"{str(workspace_root_container_path)}:{self.args.resources_dir_container_path}"
        )

        # Container Environment
        container_env: Dict[str, str] = {
            # Env variables used by data workflows and data assets
            "PHI_WORKSPACE_MOUNT": str(self.args.workspace_mount_container_path),
            "PHI_WORKSPACE_ROOT": str(workspace_root_container_path),
            "PYTHONPATH": python_path,
            PHIDATA_RUNTIME_ENV_VAR: "docker",
            SCRIPTS_DIR_ENV_VAR: str(scripts_dir_container_path),
            STORAGE_DIR_ENV_VAR: str(storage_dir_container_path),
            META_DIR_ENV_VAR: str(meta_dir_container_path),
            PRODUCTS_DIR_ENV_VAR: str(products_dir_container_path),
            NOTEBOOKS_DIR_ENV_VAR: str(notebooks_dir_container_path),
            WORKSPACE_CONFIG_DIR_ENV_VAR: str(workspace_config_dir_container_path),
            "INSTALL_REQUIREMENTS": str(self.args.install_requirements),
            "REQUIREMENTS_FILE_PATH": str(requirements_file_container_path),
            "MOUNT_WORKSPACE": str(self.args.mount_workspace),
            "MOUNT_RESOURCES": str(self.args.mount_resources),
            # Print env when the container starts
            "LOAD_EXAMPLES": str(self.args.load_examples),
            "PRINT_ENV_ON_LOAD": str(self.args.print_env_on_load),
        }

        if self.args.jupyter_config_file is not None:
            container_env["JUPYTER_CONFIG_FILE"] = self.args.jupyter_config_file

        # Update the container env using env_file
        env_data_from_file = self.get_env_data()
        if env_data_from_file is not None:
            container_env.update(env_data_from_file)

        # Update the container env using secrets_file or a secrets backend
        secret_data_from_file = self.get_secret_data()
        if secret_data_from_file is not None:
            container_env.update(secret_data_from_file)

        # Update the container env with user provided env, this overwrites any existing variables
        if self.args.env is not None and isinstance(self.args.env, dict):
            container_env.update(self.args.env)

        # Container Volumes
        # container_volumes is a dictionary which configures the volumes to mount
        # inside the container. The key is either the host path or a volume name,
        # and the value is a dictionary with 2 keys:
        #   bind - The path to mount the volume inside the container
        #   mode - Either rw to mount the volume read/write, or ro to mount it read-only.
        # For example:
        # {
        #   '/home/user1/': {'bind': '/mnt/vol2', 'mode': 'rw'},
        #   '/var/www': {'bind': '/mnt/vol1', 'mode': 'ro'}
        # }
        container_volumes = self.args.container_volumes_docker or {}
        # Create a volume for the workspace dir
        if self.args.mount_workspace:
            workspace_root_path_str = str(self.workspace_root_path)
            workspace_root_container_path_str = str(workspace_root_container_path)
            logger.debug(f"Mounting: {workspace_root_path_str}")
            logger.debug(f"\tto: {workspace_root_container_path_str}")
            container_volumes[workspace_root_path_str] = {
                "bind": workspace_root_container_path_str,
                "mode": "rw",
            }
        # Create a volume for the resources
        if self.args.mount_resources:
            resources_dir_path = str(
                self.workspace_root_path.joinpath(self.args.resources_dir)
            )
            logger.debug(f"Mounting: {resources_dir_path}")
            logger.debug(f"\tto: {self.args.resources_dir_container_path}")
            container_volumes[resources_dir_path] = {
                "bind": self.args.resources_dir_container_path,
                "mode": "ro",
            }

        # Container Ports
        # container_ports is a dictionary which configures the ports to bind
        # inside the container. The key is the port to bind inside the container
        #   either as an integer or a string in the form port/protocol
        # and the value is the corresponding port to open on the host.
        # For example:
        #   {'2222/tcp': 3333} will expose port 2222 inside the container as port 3333 on the host.
        container_ports: Dict[str, int] = self.args.container_ports_docker or {}

        # if open_container_port = True
        if self.args.open_container_port:
            container_ports[
                str(self.args.container_port)
            ] = self.args.container_host_port

        # if open_app_port = True
        # 1. Set the app_port in the container env
        # 2. Open the app_port
        if self.args.open_app_port:
            # Open the port
            container_ports[str(self.args.app_port)] = self.args.app_host_port

        container_cmd: List[str] = []
        if isinstance(self.args.command, str):
            container_cmd = [self.args.command]
        else:
            container_cmd = self.args.command
        if self.args.jupyter_config_file is not None:
            config_file_container_path = workspace_root_container_path.joinpath(
                self.args.jupyter_config_file
            )
            if config_file_container_path is not None:
                container_cmd.append(f" --config={str(config_file_container_path)}")
        if (
            self.args.use_workspace_as_notebook_dir
            and self.args.workspace_mount_container_path is not None
        ):
            container_cmd.append(
                f" --notebook-dir={str(self.args.workspace_mount_container_path)}"
            )

        # Create the container
        docker_container = DockerContainer(
            name=self.get_container_name(),
            image=get_image_str(self.args.image_name, self.args.image_tag),
            entrypoint=self.args.entrypoint,
            command=" ".join(container_cmd),
            detach=self.args.container_detach,
            auto_remove=self.args.container_auto_remove,
            healthcheck=self.args.container_healthcheck,
            hostname=self.args.container_hostname,
            labels=self.args.container_labels,
            environment=container_env,
            network=docker_build_context.network,
            platform=self.args.container_platform,
            ports=container_ports if len(container_ports) > 0 else None,
            remove=self.args.container_remove,
            restart_policy=self.args.container_restart_policy_docker,
            stdin_open=self.args.container_stdin_open,
            tty=self.args.container_tty,
            user=self.args.container_user,
            volumes=container_volumes,
            working_dir=self.args.container_working_dir,
            use_cache=self.args.use_cache,
        )
        # logger.debug(f"Container Env: {docker_container.environment}")

        docker_rg = DockerResourceGroup(
            name=app_name,
            enabled=self.args.enabled,
            network=DockerNetwork(name=docker_build_context.network),
            containers=[docker_container],
        )
        return docker_rg

    def init_docker_resource_groups(
        self, docker_build_context: DockerBuildContext
    ) -> None:
        docker_rg = self.get_docker_rg(docker_build_context)
        if docker_rg is not None:
            if self.docker_resource_groups is None:
                self.docker_resource_groups = OrderedDict()
            self.docker_resource_groups[docker_rg.name] = docker_rg

    ######################################################
    ## K8s Resources
    ######################################################

    def get_k8s_rg(
        self, k8s_build_context: K8sBuildContext
    ) -> Optional[K8sResourceGroup]:

        return None

        # app_name = self.args.name
        # logger.debug(f"Building {app_name} K8sResourceGroup")
        #
        # # Define K8s resources
        # config_maps: List[CreateConfigMap] = []
        # secrets: List[CreateSecret] = []
        # volumes: List[CreateVolume] = []
        # containers: List[CreateContainer] = []
        # services: List[CreateService] = []
        # ports: List[CreatePort] = []
        #
        # # Workspace paths
        # if self.workspace_root_path is None:
        #     logger.error("Invalid workspace_root_path")
        #     return None
        # workspace_name = self.workspace_root_path.stem
        # workspace_root_container_path = Path(
        #     self.args.workspace_mount_container_path
        # ).joinpath(workspace_name)
        # requirements_file_container_path = workspace_root_container_path.joinpath(
        #     self.args.requirements_file_path
        # )
        # scripts_dir_container_path = (
        #     workspace_root_container_path.joinpath(self.scripts_dir)
        #     if self.scripts_dir
        #     else None
        # )
        # storage_dir_container_path = (
        #     workspace_root_container_path.joinpath(self.storage_dir)
        #     if self.storage_dir
        #     else None
        # )
        # meta_dir_container_path = (
        #     workspace_root_container_path.joinpath(self.meta_dir)
        #     if self.meta_dir
        #     else None
        # )
        # products_dir_container_path = (
        #     workspace_root_container_path.joinpath(self.products_dir)
        #     if self.products_dir
        #     else None
        # )
        # notebooks_dir_container_path = (
        #     workspace_root_container_path.joinpath(self.notebooks_dir)
        #     if self.notebooks_dir
        #     else None
        # )
        # workspace_config_dir_container_path = (
        #     workspace_root_container_path.joinpath(self.workspace_config_dir)
        #     if self.workspace_config_dir
        #     else None
        # )
        #
        # # Container pythonpath
        # python_path = (
        #     self.args.python_path
        #     or f"{str(workspace_root_container_path)}:{self.args.resources_dir_container_path}"
        # )
        #
        # # Container Environment
        # container_env: Dict[str, str] = {
        #     # Env variables used by data workflows and data assets
        #     "PHI_WORKSPACE_MOUNT": str(self.args.workspace_mount_container_path),
        #     "PHI_WORKSPACE_ROOT": str(workspace_root_container_path),
        #     "PYTHONPATH": python_path,
        #     PHIDATA_RUNTIME_ENV_VAR: "kubernetes",
        #     SCRIPTS_DIR_ENV_VAR: str(scripts_dir_container_path),
        #     STORAGE_DIR_ENV_VAR: str(storage_dir_container_path),
        #     META_DIR_ENV_VAR: str(meta_dir_container_path),
        #     PRODUCTS_DIR_ENV_VAR: str(products_dir_container_path),
        #     NOTEBOOKS_DIR_ENV_VAR: str(notebooks_dir_container_path),
        #     WORKSPACE_CONFIG_DIR_ENV_VAR: str(workspace_config_dir_container_path),
        #     "INSTALL_REQUIREMENTS": str(self.args.install_requirements),
        #     "REQUIREMENTS_FILE_PATH": str(requirements_file_container_path),
        #     "REQUIREMENTS_LOCAL": str(requirements_file_container_path),
        #     # Print env when the container starts
        #     "PRINT_ENV_ON_LOAD": str(self.args.print_env_on_load),
        # }
        #
        # # Update the container env using env_file
        # env_data_from_file = self.get_env_data_from_file()
        # if env_data_from_file is not None:
        #     container_env.update(env_data_from_file)
        #
        # # Update the container env with user provided env
        # if self.args.env is not None and isinstance(self.args.env, dict):
        #     container_env.update(self.args.env)
        #
        # # Create a ConfigMap to set the container env variables which are not Secret
        # container_env_cm = CreateConfigMap(
        #     cm_name=self.args.config_map_name or get_default_configmap_name(app_name),
        #     app_name=app_name,
        #     data=container_env,
        # )
        # # logger.debug(f"ConfigMap {container_env_cm.cm_name}: {container_env_cm.json(indent=2)}")
        # config_maps.append(container_env_cm)
        #
        # # Create a Secret to set the container env variables which are Secret
        # secret_data_from_file = self.get_secret_data_from_file()
        # if secret_data_from_file is not None:
        #     container_env_secret = CreateSecret(
        #         secret_name=self.args.secret_name or get_default_secret_name(app_name),
        #         app_name=app_name,
        #         string_data=secret_data_from_file,
        #     )
        #     secrets.append(container_env_secret)
        #
        # # If mount_workspace=True first check if the workspace
        # # should be mounted locally, otherwise
        # # Create a Sidecar git-sync container and volume
        # if self.args.mount_workspace:
        #     workspace_volume_name = (
        #         self.args.workspace_volume_name or get_default_volume_name(app_name)
        #     )
        #
        #     if self.args.k8s_mount_local_workspace:
        #         workspace_root_path_str = str(self.workspace_root_path)
        #         workspace_root_container_path_str = str(workspace_root_container_path)
        #         logger.debug(f"Mounting: {workspace_root_path_str}")
        #         logger.debug(f"\tto: {workspace_root_container_path_str}")
        #         workspace_volume = CreateVolume(
        #             volume_name=workspace_volume_name,
        #             app_name=app_name,
        #             mount_path=workspace_root_container_path_str,
        #             volume_type=VolumeType.HOST_PATH,
        #             host_path=HostPathVolumeSource(
        #                 path=workspace_root_path_str,
        #             ),
        #         )
        #         volumes.append(workspace_volume)
        #
        #     elif self.args.create_git_sync_sidecar:
        #         workspace_mount_container_path_str = str(
        #             self.args.workspace_mount_container_path
        #         )
        #         logger.debug(f"Creating EmptyDir")
        #         logger.debug(f"\tat: {workspace_mount_container_path_str}")
        #         workspace_volume = CreateVolume(
        #             volume_name=workspace_volume_name,
        #             app_name=app_name,
        #             mount_path=workspace_mount_container_path_str,
        #             volume_type=VolumeType.EMPTY_DIR,
        #         )
        #         volumes.append(workspace_volume)
        #
        #         if self.args.git_sync_repo is None:
        #             print_error("git_sync_repo invalid")
        #         else:
        #             git_sync_env = {
        #                 "GIT_SYNC_REPO": self.args.git_sync_repo,
        #                 "GIT_SYNC_ROOT": str(self.args.workspace_mount_container_path),
        #                 "GIT_SYNC_DEST": workspace_name,
        #             }
        #             if self.args.git_sync_branch is not None:
        #                 git_sync_env["GIT_SYNC_BRANCH"] = self.args.git_sync_branch
        #             if self.args.git_sync_wait is not None:
        #                 git_sync_env["GIT_SYNC_WAIT"] = str(self.args.git_sync_wait)
        #             git_sync_sidecar = CreateContainer(
        #                 container_name="git-sync-workspaces",
        #                 app_name=app_name,
        #                 image_name="k8s.gcr.io/git-sync",
        #                 image_tag="v3.1.1",
        #                 env=git_sync_env,
        #                 envs_from_configmap=[cm.cm_name for cm in config_maps]
        #                 if len(config_maps) > 0
        #                 else None,
        #                 envs_from_secret=[secret.secret_name for secret in secrets]
        #                 if len(secrets) > 0
        #                 else None,
        #                 volumes=[workspace_volume],
        #             )
        #             containers.append(git_sync_sidecar)
        #
        # # Create the ports to open
        # # if open_container_port = True
        # if self.args.open_container_port:
        #     container_port = CreatePort(
        #         name=self.args.container_port_name,
        #         container_port=self.args.container_port,
        #     )
        #     ports.append(container_port)
        #
        # # if open_app_port = True
        # # 1. Set the app_port in the container env
        # # 2. Open the jupyter app port
        # app_port: Optional[CreatePort] = None
        # if self.args.open_app_port:
        #     # Open the port
        #     app_port = CreatePort(
        #         name=self.args.app_port_name,
        #         container_port=self.args.app_port,
        #         service_port=self.get_app_service_port(),
        #         node_port=self.args.app_node_port,
        #         target_port=self.args.app_target_port or self.args.app_port_name,
        #     )
        #     ports.append(app_port)
        #
        # container_labels: Optional[Dict[str, Any]] = self.args.container_labels
        # if k8s_build_context.labels is not None:
        #     if container_labels:
        #         container_labels.update(k8s_build_context.labels)
        #     else:
        #         container_labels = k8s_build_context.labels
        #
        # # Equivalent to docker images CMD
        # container_args: List[str] = []
        # if isinstance(self.args.command, str):
        #     container_args = [self.args.command]
        # else:
        #     container_args = self.args.command
        # if self.args.jupyter_config_file is not None:
        #     config_file_container_path = workspace_root_container_path.joinpath(
        #         self.args.jupyter_config_file
        #     )
        #     if config_file_container_path is not None:
        #         container_args.append(f" --config={str(config_file_container_path)}")
        # if (
        #     self.args.use_workspace_as_notebook_dir is not None
        #     and workspace_root_container_path is not None
        # ):
        #     container_args.append(
        #         f" --notebook-dir={str(workspace_root_container_path)}"
        #     )
        #
        # # Create the container
        # k8s_container = CreateContainer(
        #     container_name=self.get_container_name(),
        #     app_name=app_name,
        #     image_name=self.args.image_name,
        #     image_tag=self.args.image_tag,
        #     args=container_args,
        #     # Equivalent to docker images ENTRYPOINT
        #     command=[self.args.entrypoint]
        #     if isinstance(self.args.entrypoint, str)
        #     else self.args.entrypoint,
        #     image_pull_policy=self.args.image_pull_policy,
        #     envs_from_configmap=[cm.cm_name for cm in config_maps]
        #     if len(config_maps) > 0
        #     else None,
        #     envs_from_secret=[secret.secret_name for secret in secrets]
        #     if len(secrets) > 0
        #     else None,
        #     ports=ports if len(ports) > 0 else None,
        #     volumes=volumes if len(volumes) > 0 else None,
        #     labels=container_labels,
        # )
        # containers.append(k8s_container)
        #
        # # Set default container for kubectl commands
        # # https://kubernetes.io/docs/reference/labels-annotations-taints/#kubectl-kubernetes-io-default-container
        # pod_annotations = {
        #     "kubectl.kubernetes.io/default-container": k8s_container.container_name
        # }
        #
        # deploy_labels: Optional[Dict[str, Any]] = self.args.deploy_labels
        # if k8s_build_context.labels is not None:
        #     if deploy_labels:
        #         deploy_labels.update(k8s_build_context.labels)
        #     else:
        #         deploy_labels = k8s_build_context.labels
        # # Create the deployment
        # k8s_deployment = CreateDeployment(
        #     replicas=self.args.replicas,
        #     deploy_name=self.args.deploy_name or get_default_deploy_name(app_name),
        #     pod_name=self.args.pod_name or get_default_pod_name(app_name),
        #     app_name=app_name,
        #     namespace=k8s_build_context.namespace,
        #     service_account_name=k8s_build_context.service_account_name,
        #     containers=containers if len(containers) > 0 else None,
        #     pod_node_selector=self.args.pod_node_selector,
        #     restart_policy=self.args.restart_policy,
        #     termination_grace_period_seconds=self.args.termination_grace_period_seconds,
        #     volumes=volumes if len(volumes) > 0 else None,
        #     labels=deploy_labels,
        #     pod_annotations=pod_annotations,
        #     topology_spread_key=self.args.topology_spread_key,
        #     topology_spread_max_skew=self.args.topology_spread_max_skew,
        #     topology_spread_when_unsatisfiable=self.args.topology_spread_when_unsatisfiable,
        # )
        #
        # # Create the services
        # if self.args.create_app_service:
        #     app_service_labels: Optional[Dict[str, Any]] = self.args.app_service_labels
        #     if k8s_build_context.labels is not None:
        #         if app_service_labels:
        #             app_service_labels.update(k8s_build_context.labels)
        #         else:
        #             app_service_labels = k8s_build_context.labels
        #     app_service = CreateService(
        #         service_name=self.get_app_service_name(),
        #         app_name=app_name,
        #         namespace=k8s_build_context.namespace,
        #         service_account_name=k8s_build_context.service_account_name,
        #         service_type=self.args.app_service_type,
        #         deployment=k8s_deployment,
        #         ports=[app_port] if app_port else None,
        #         labels=app_service_labels,
        #     )
        #     services.append(app_service)
        #
        # # Create the K8sResourceGroup
        # k8s_resource_group = CreateK8sResourceGroup(
        #     name=app_name,
        #     enabled=self.args.enabled,
        #     config_maps=config_maps if len(config_maps) > 0 else None,
        #     secrets=secrets if len(secrets) > 0 else None,
        #     services=services if len(services) > 0 else None,
        #     deployments=[k8s_deployment],
        # )
        #
        # return k8s_resource_group.create()

    def init_k8s_resource_groups(self, k8s_build_context: K8sBuildContext) -> None:

        logger.warning("JupyterLab is not yet available on kubernetes")

        k8s_rg = self.get_k8s_rg(k8s_build_context)
        if k8s_rg is not None:
            if self.k8s_resource_groups is None:
                self.k8s_resource_groups = OrderedDict()
            self.k8s_resource_groups[k8s_rg.name] = k8s_rg

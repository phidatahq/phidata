from collections import OrderedDict
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from typing_extensions import Literal

from phidata.app.db import DbApp
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


class SupersetBaseArgs(PhidataAppArgs):
    name: str = "superset"
    version: str = "1"
    enabled: bool = True

    # Image args
    image_name: str = "phidata/superset"
    image_tag: str = "2.0.0"
    entrypoint: Optional[Union[str, List]] = None
    command: Optional[Union[str, List]] = None

    # Install python dependencies using a requirements.txt file
    # Sets the REQUIREMENTS_LOCAL & REQUIREMENTS_FILE_PATH env var to requirements_file_path
    install_requirements: bool = False
    # Path to the requirements.txt file relative to the workspace_root
    requirements_file_path: str = "requirements.txt"

    # Configure Superset db
    wait_for_db: bool = False
    # Connect to database using a DbApp
    db_app: Optional[DbApp] = None
    # Provide database connection details manually
    # db_user can be provided here or as the
    # DATABASE_USER env var in the secrets_file
    db_user: Optional[str] = None
    # db_password can be provided here or as the
    # DATABASE_PASSWORD env var in the secrets_file
    db_password: Optional[str] = None
    # db_schema can be provided here or as the
    # DATABASE_DB env var in the secrets_file
    db_schema: Optional[str] = None
    # db_host can be provided here or as the
    # DATABASE_HOST env var in the secrets_file
    db_host: Optional[str] = None
    # db_port can be provided here or as the
    # DATABASE_PORT env var in the secrets_file
    db_port: Optional[int] = None
    # db_driver can be provided here or as the
    # DATABASE_DIALECT env var in the secrets_file
    db_dialect: Optional[str] = None

    # Configure superset redis
    wait_for_redis: bool = False
    # Connect to redis using a PhidataApp
    redis_app: Optional[DbApp] = None
    # redis_host can be provided here or as the
    # REDIS_HOST env var in the secrets_file
    redis_host: Optional[str] = None
    # redis_port can be provided here or as the
    # REDIS_PORT env var in the secrets_file
    redis_port: Optional[int] = None
    # redis_driver can be provided here or as the
    # REDIS_DRIVER env var in the secrets_file
    redis_driver: Optional[str] = None

    # Configure the superset container
    container_name: Optional[str] = None
    # Set the SUPERSET_CONFIG_PATH env var
    superset_config_path: Optional[str] = None
    # Set the FLASK_ENV env var
    flask_env: str = "production"
    # Set the SUPERSET_ENV env var
    superset_env: str = "production"
    # Set the PYTHONPATH env var
    # defaults to "/app/pythonpath:/app/docker/pythonpath_dev"
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
    container_platform: Optional[str] = None
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
    open_app_port: bool = False
    # App port number on the container
    # Set the SUPERSET_PORT env var
    app_port: int = 8088
    # Only used by the K8sContainer
    app_port_name: str = "app"
    # Only used by the DockerContainer
    app_host_port: int = 8088

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
    create_git_sync_sidecar: bool = False
    create_git_sync_init_container: bool = True
    git_sync_repo: Optional[str] = None
    git_sync_branch: Optional[str] = None
    git_sync_wait: int = 1
    # When running k8s locally, we can mount the workspace using host path as well.
    k8s_mount_local_workspace = False

    # Configure resources volume - only on docker
    # Superset resources directory relative to the workspace_root
    # This directory contains all the files required by superset.
    # eg: docker-bootstrap.sh
    # This dir is mounted to the `/app/docker` directory on the container
    mount_resources: bool = False
    resources_dir: str = "workspace/superset"
    resources_dir_container_path: str = "/app/docker"
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
    create_app_service: bool = False
    app_svc_name: Optional[str] = None
    app_svc_type: Optional[ServiceType] = None
    # The port that will be exposed by the service.
    app_svc_port: int = 8088
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
    # Set SUPERSET_LOAD_EXAMPLES = "yes"
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


class SupersetBase(PhidataApp):
    def __init__(
        self,
        name: str = "superset",
        version: str = "1",
        enabled: bool = True,
        # Image args,
        image_name: str = "phidata/superset",
        image_tag: str = "2.0.0",
        entrypoint: Optional[Union[str, List]] = None,
        command: Optional[Union[str, List]] = None,
        # Install python dependencies using a requirements.txt file,
        # Sets the REQUIREMENTS_LOCAL & REQUIREMENTS_FILE_PATH env var to requirements_file_path,
        install_requirements: bool = False,
        # Path to the requirements.txt file relative to the workspace_root,
        requirements_file_path: str = "requirements.txt",
        # Configure Superset db,
        wait_for_db: bool = False,
        # Connect to database using a DbApp,
        db_app: Optional[DbApp] = None,
        # Provide database connection details manually,
        # db_user can be provided here or as the,
        # DATABASE_USER env var in the secrets_file,
        db_user: Optional[str] = None,
        # db_password can be provided here or as the,
        # DATABASE_PASSWORD env var in the secrets_file,
        db_password: Optional[str] = None,
        # db_schema can be provided here or as the,
        # DATABASE_DB env var in the secrets_file,
        db_schema: Optional[str] = None,
        # db_host can be provided here or as the,
        # DATABASE_HOST env var in the secrets_file,
        db_host: Optional[str] = None,
        # db_port can be provided here or as the,
        # DATABASE_PORT env var in the secrets_file,
        db_port: Optional[int] = None,
        # db_driver can be provided here or as the,
        # DATABASE_DIALECT env var in the secrets_file,
        db_dialect: Optional[str] = None,
        # Configure superset redis,
        wait_for_redis: bool = False,
        # Connect to redis using a PhidataApp,
        redis_app: Optional[DbApp] = None,
        # redis_host can be provided here or as the,
        # REDIS_HOST env var in the secrets_file,
        redis_host: Optional[str] = None,
        # redis_port can be provided here or as the,
        # REDIS_PORT env var in the secrets_file,
        redis_port: Optional[int] = None,
        # redis_driver can be provided here or as the,
        # REDIS_DRIVER env var in the secrets_file,
        redis_driver: Optional[str] = None,
        # Configure the superset container,
        container_name: Optional[str] = None,
        # Set the SUPERSET_CONFIG_PATH env var,
        superset_config_path: Optional[str] = None,
        # Set the FLASK_ENV env var,
        flask_env: str = "production",
        # Set the SUPERSET_ENV env var,
        superset_env: str = "production",
        # Set the PYTHONPATH env var,
        # defaults to "/app/pythonpath:/app/docker/pythonpath_dev",
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
        container_platform: Optional[str] = None,
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
        open_app_port: bool = False,
        # App port number on the container,
        # Set the SUPERSET_PORT env var,
        app_port: int = 8088,
        # Only used by the K8sContainer,
        app_port_name: str = "app",
        # Only used by the DockerContainer,
        app_host_port: int = 8088,
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
        # eg: if ws name is: idata, workspace_dir would be: /workspaces/idata,
        # eg: if ws name is: idata, workspace_root would be: /mnt/workspaces/idata,
        workspace_mount_container_path: str = "/mnt/workspaces",
        # NOTE: On DockerContainers the local workspace_root_path is mounted under workspace_mount_container_path,
        # because we assume that DockerContainers are running locally on the user's machine,
        # On K8sContainers, we load the workspace_dir from git using a git-sync sidecar container,
        create_git_sync_sidecar: bool = False,
        create_git_sync_init_container: bool = True,
        git_sync_repo: Optional[str] = None,
        git_sync_branch: Optional[str] = None,
        git_sync_wait: int = 1,
        # When running k8s locally, we can mount the workspace using host path as well.,
        k8s_mount_local_workspace=False,
        # Configure resources volume - only on docker,
        # Superset resources directory relative to the workspace_root,
        # This directory contains all the files required by superset.,
        # eg: docker-bootstrap.sh,
        # This dir is mounted to the `/app/docker` directory on the container,
        mount_resources: bool = False,
        resources_dir: str = "workspace/superset",
        resources_dir_container_path: str = "/app/docker",
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
        create_app_service: bool = False,
        app_svc_name: Optional[str] = None,
        app_svc_type: Optional[ServiceType] = None,
        # The port that will be exposed by the service.,
        app_svc_port: int = 8088,
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
        # Set SUPERSET_LOAD_EXAMPLES = "yes",
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
            self.args: SupersetBaseArgs = SupersetBaseArgs(
                name=name,
                version=version,
                enabled=enabled,
                image_name=image_name,
                image_tag=image_tag,
                entrypoint=entrypoint,
                command=command,
                install_requirements=install_requirements,
                requirements_file_path=requirements_file_path,
                wait_for_db=wait_for_db,
                db_app=db_app,
                db_user=db_user,
                db_password=db_password,
                db_schema=db_schema,
                db_host=db_host,
                db_port=db_port,
                db_dialect=db_dialect,
                wait_for_redis=wait_for_redis,
                redis_app=redis_app,
                redis_host=redis_host,
                redis_port=redis_port,
                redis_driver=redis_driver,
                container_name=container_name,
                superset_config_path=superset_config_path,
                flask_env=flask_env,
                superset_env=superset_env,
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
                create_app_service=create_app_service,
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

    def get_db_user(self) -> Optional[str]:
        db_user_var: Optional[str] = self.args.db_user if self.args else None
        if db_user_var is None:
            # read from secrets_file
            logger.debug(f"Reading DATABASE_USER from secrets")
            secret_data = self.get_secret_data()
            if secret_data is not None:
                db_user_var = secret_data.get("DATABASE_USER", db_user_var)
        return db_user_var

    def get_db_password(self) -> Optional[str]:
        db_password_var: Optional[str] = self.args.db_password if self.args else None
        if db_password_var is None:
            # read from secrets_file
            logger.debug(f"Reading DATABASE_PASSWORD from secrets")
            secret_data = self.get_secret_data()
            if secret_data is not None:
                db_password_var = secret_data.get("DATABASE_PASSWORD", db_password_var)
        return db_password_var

    def get_db_schema(self) -> Optional[str]:
        db_schema_var: Optional[str] = self.args.db_schema if self.args else None
        if db_schema_var is None:
            # read from secrets_file
            logger.debug(f"Reading DATABASE_DB from secrets")
            secret_data = self.get_secret_data()
            if secret_data is not None:
                db_schema_var = secret_data.get("DATABASE_DB", db_schema_var)
        return db_schema_var

    def get_db_host(self) -> Optional[str]:
        db_host_var: Optional[str] = self.args.db_host if self.args else None
        if db_host_var is None:
            # read from secrets_file
            logger.debug(f"Reading DATABASE_HOST from secrets")
            secret_data = self.get_secret_data()
            if secret_data is not None:
                db_host_var = secret_data.get("DATABASE_HOST", db_host_var)
        return db_host_var

    def get_db_port(self) -> Optional[str]:
        db_port_var: Optional[Union[int, str]] = (
            self.args.db_port if self.args else None
        )
        if db_port_var is None:
            # read from secrets_file
            logger.debug(f"Reading DATABASE_PORT from secrets")
            secret_data = self.get_secret_data()
            if secret_data is not None:
                db_port_var = secret_data.get("DATABASE_PORT", db_port_var)
        return str(db_port_var) if db_port_var is not None else db_port_var

    def get_db_dialect(self) -> Optional[str]:
        db_dialect_var: Optional[str] = self.args.db_dialect if self.args else None
        if db_dialect_var is None:
            # read from secrets_file
            logger.debug(f"Reading DATABASE_DIALECT from secrets")
            secret_data = self.get_secret_data()
            if secret_data is not None:
                db_dialect_var = secret_data.get("DATABASE_DIALECT", db_dialect_var)
        return db_dialect_var

    def get_redis_host(self) -> Optional[str]:
        redis_host_var: Optional[str] = self.args.redis_host if self.args else None
        if redis_host_var is None:
            # read from secrets_file
            logger.debug(f"Reading REDIS_HOST from secrets")
            secret_data = self.get_secret_data()
            if secret_data is not None:
                redis_host_var = secret_data.get("REDIS_HOST", redis_host_var)
        return redis_host_var

    def get_redis_port(self) -> Optional[str]:
        redis_port_var: Optional[Union[int, str]] = (
            self.args.redis_port if self.args else None
        )
        if redis_port_var is None:
            # read from secrets_file
            logger.debug(f"Reading REDIS_PORT from secrets")
            secret_data = self.get_secret_data()
            if secret_data is not None:
                redis_port_var = secret_data.get("REDIS_PORT", redis_port_var)
        return str(redis_port_var) if redis_port_var is not None else redis_port_var

    def get_redis_driver(self) -> Optional[str]:
        redis_driver_var: Optional[str] = self.args.redis_driver if self.args else None
        if redis_driver_var is None:
            # read from secrets_file
            logger.debug(f"Reading REDIS_DRIVER from secrets")
            secret_data = self.get_secret_data()
            if secret_data is not None:
                redis_driver_var = secret_data.get("REDIS_DRIVER", redis_driver_var)
        return redis_driver_var

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
            or f"/app/pythonpath:{self.args.resources_dir_container_path}/pythonpath_dev"
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
            "REQUIREMENTS_LOCAL": str(requirements_file_container_path),
            "MOUNT_WORKSPACE": str(self.args.mount_workspace),
            "MOUNT_RESOURCES": str(self.args.mount_resources),
            "WAIT_FOR_DB": str(self.args.wait_for_db),
            "WAIT_FOR_REDIS": str(self.args.wait_for_redis),
            "SUPERSET_LOAD_EXAMPLES": "yes" if self.args.load_examples else "no",
            # Print env when the container starts
            "PRINT_ENV_ON_LOAD": str(self.args.print_env_on_load),
        }

        # Set airflow env vars
        self.set_aws_env_vars(env_dict=container_env)

        if self.args.superset_config_path is not None:
            container_env["SUPERSET_CONFIG_PATH"] = self.args.superset_config_path

        if self.args.flask_env is not None:
            container_env["FLASK_ENV"] = self.args.flask_env

        if self.args.superset_env is not None:
            container_env["SUPERSET_ENV"] = self.args.superset_env

        # Superset db connection
        db_user = self.get_db_user()
        db_password = self.get_db_password()
        db_schema = self.get_db_schema()
        db_host = self.get_db_host()
        db_port = self.get_db_port()
        db_dialect = self.get_db_dialect()
        if self.args.db_app is not None and isinstance(self.args.db_app, DbApp):
            logger.debug(f"Reading db connection details from: {self.args.db_app.name}")
            if db_user is None:
                db_user = self.args.db_app.get_db_user()
            if db_password is None:
                db_password = self.args.db_app.get_db_password()
            if db_schema is None:
                db_schema = self.args.db_app.get_db_schema()
            if db_host is None:
                db_host = self.args.db_app.get_db_host_docker()
            if db_port is None:
                db_port = str(self.args.db_app.get_db_port_docker())
            if db_dialect is None:
                db_dialect = self.args.db_app.get_db_driver()

        if db_user is not None:
            container_env["DATABASE_USER"] = db_user
        # Ideally we dont want the password in the env
        # But the superest image expects it :(
        if db_password is not None:
            container_env["DATABASE_PASSWORD"] = db_password
        if db_schema is not None:
            container_env["DATABASE_DB"] = db_schema
        if db_host is not None:
            container_env["DATABASE_HOST"] = db_host
        if db_port is not None:
            container_env["DATABASE_PORT"] = str(db_port)
        if db_dialect is not None:
            container_env["DATABASE_DIALECT"] = db_dialect

        # Superset redis connection
        redis_host = self.get_redis_host()
        redis_port = self.get_redis_port()
        redis_driver = self.get_redis_driver()
        if self.args.redis_app is not None and isinstance(self.args.redis_app, DbApp):
            logger.debug(
                f"Reading redis connection details from: {self.args.redis_app.name}"
            )
            if redis_host is None:
                redis_host = self.args.redis_app.get_db_host_docker()
            if redis_port is None:
                redis_port = str(self.args.redis_app.get_db_port_docker())
            if redis_driver is None:
                redis_driver = self.args.redis_app.get_db_driver()

        if redis_host is not None:
            container_env["REDIS_HOST"] = redis_host
        if redis_port is not None:
            container_env["REDIS_PORT"] = str(redis_port)
        if redis_driver is not None:
            container_env["REDIS_DRIVER"] = str(redis_driver)

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
            # Set the app port in the container_env
            container_env["SUPERSET_PORT"] = str(self.args.app_port)
            # Open the port
            container_ports[str(self.args.app_port)] = self.args.app_host_port

        # Create the container
        docker_container = DockerContainer(
            name=self.get_container_name(),
            image=get_image_str(self.args.image_name, self.args.image_tag),
            entrypoint=self.args.entrypoint,
            command=self.args.command,
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

        app_name = self.args.name
        logger.debug(f"Building {app_name} K8sResourceGroup")

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

        # Init K8s resources for the CreateK8sResourceGroup
        ns: Optional[CreateNamespace] = self.args.namespace
        sa: Optional[CreateServiceAccount] = self.args.service_account
        cr: Optional[CreateClusterRole] = self.args.cluster_role
        crb: Optional[CreateClusterRoleBinding] = self.args.cluster_role_binding
        secrets: List[CreateSecret] = self.args.extra_secrets or []
        config_maps: List[CreateConfigMap] = self.args.extra_config_maps or []
        storage_classes: List[CreateStorageClass] = (
            self.args.extra_storage_classes or []
        )
        services: List[CreateService] = self.args.extra_services or []
        deployments: List[CreateDeployment] = self.args.extra_deployments or []
        custom_objects: List[CreateCustomObject] = self.args.extra_custom_objects or []
        crds: List[CreateCustomResourceDefinition] = self.args.extra_crds or []
        pvs: List[CreatePersistentVolume] = self.args.extra_pvs or []
        pvcs: List[CreatePVC] = self.args.extra_pvcs or []
        containers: List[CreateContainer] = self.args.extra_containers or []
        init_containers: List[CreateContainer] = self.args.extra_init_containers or []
        ports: List[CreatePort] = self.args.extra_ports or []
        volumes: List[CreateVolume] = self.args.extra_volumes or []

        # Common variables used by all resources
        ns_name: str = self.args.ns_name or k8s_build_context.namespace
        sa_name: Optional[str] = (
            self.args.sa_name or k8s_build_context.service_account_name
        )
        common_labels: Optional[Dict[str, str]] = k8s_build_context.labels

        # -*- Define RBAC resources
        # WebUI/Scheduler pods should run with serviceAccount which have RBAC
        # permissions on the k8s cluster to get logs
        # https://github.com/apache/airflow/issues/11696#issuecomment-715886117
        if self.args.use_rbac:
            if ns is None:
                ns = CreateNamespace(
                    ns=ns_name,
                    app_name=app_name,
                    labels=common_labels,
                )
            ns_name = ns.ns
            if sa is None:
                sa = CreateServiceAccount(
                    sa_name=sa_name or get_default_sa_name(app_name),
                    app_name=app_name,
                    namespace=ns_name,
                )
            sa_name = sa.sa_name
            if cr is None:
                cr = CreateClusterRole(
                    cr_name=self.args.cr_name or get_default_cr_name(app_name),
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
            if crb is None:
                crb = CreateClusterRoleBinding(
                    crb_name=self.args.crb_name or get_default_crb_name(app_name),
                    cr_name=cr.cr_name,
                    service_account_name=sa.sa_name,
                    app_name=app_name,
                    namespace=ns_name,
                    labels=common_labels,
                )

        # Container pythonpath
        python_path = (
            self.args.python_path
            or f"/app/pythonpath:{self.args.resources_dir_container_path}/pythonpath_dev"
        )

        # Container Environment
        container_env: Dict[str, str] = {
            # Env variables used by data workflows and data assets
            "PHI_WORKSPACE_MOUNT": str(self.args.workspace_mount_container_path),
            "PHI_WORKSPACE_ROOT": str(workspace_root_container_path),
            "PYTHONPATH": python_path,
            PHIDATA_RUNTIME_ENV_VAR: "kubernetes",
            SCRIPTS_DIR_ENV_VAR: str(scripts_dir_container_path),
            STORAGE_DIR_ENV_VAR: str(storage_dir_container_path),
            META_DIR_ENV_VAR: str(meta_dir_container_path),
            PRODUCTS_DIR_ENV_VAR: str(products_dir_container_path),
            NOTEBOOKS_DIR_ENV_VAR: str(notebooks_dir_container_path),
            WORKSPACE_CONFIG_DIR_ENV_VAR: str(workspace_config_dir_container_path),
            "INSTALL_REQUIREMENTS": str(self.args.install_requirements),
            "REQUIREMENTS_FILE_PATH": str(requirements_file_container_path),
            "REQUIREMENTS_LOCAL": str(requirements_file_container_path),
            "MOUNT_WORKSPACE": str(self.args.mount_workspace),
            "MOUNT_RESOURCES": str(self.args.mount_resources),
            "WAIT_FOR_DB": str(self.args.wait_for_db),
            "WAIT_FOR_REDIS": str(self.args.wait_for_redis),
            "SUPERSET_LOAD_EXAMPLES": "yes" if self.args.load_examples else "no",
            # Print env when the container starts
            "PRINT_ENV_ON_LOAD": str(self.args.print_env_on_load),
        }

        # Set airflow env vars
        self.set_aws_env_vars(env_dict=container_env)

        if self.args.superset_config_path is not None:
            container_env["SUPERSET_CONFIG_PATH"] = self.args.superset_config_path

        if self.args.flask_env is not None:
            container_env["FLASK_ENV"] = self.args.flask_env

        if self.args.superset_env is not None:
            container_env["SUPERSET_ENV"] = self.args.superset_env

        # Superset db connection
        db_user = self.get_db_user()
        db_password = self.get_db_password()
        db_schema = self.get_db_schema()
        db_host = self.get_db_host()
        db_port = self.get_db_port()
        db_dialect = self.get_db_dialect()
        if self.args.db_app is not None and isinstance(self.args.db_app, DbApp):
            logger.debug(f"Reading db connection details from: {self.args.db_app.name}")
            if db_user is None:
                db_user = self.args.db_app.get_db_user()
            if db_password is None:
                db_password = self.args.db_app.get_db_password()
            if db_schema is None:
                db_schema = self.args.db_app.get_db_schema()
            if db_host is None:
                db_host = self.args.db_app.get_db_host_k8s()
            if db_port is None:
                db_port = str(self.args.db_app.get_db_port_k8s())
            if db_dialect is None:
                db_dialect = self.args.db_app.get_db_driver()

        if db_user is not None:
            container_env["DATABASE_USER"] = db_user
        # Ideally we dont want the password in the env
        # But the superest image expects it :(
        if db_password is not None:
            container_env["DATABASE_PASSWORD"] = db_password
        if db_schema is not None:
            container_env["DATABASE_DB"] = db_schema
        if db_host is not None:
            container_env["DATABASE_HOST"] = db_host
        if db_port is not None:
            container_env["DATABASE_PORT"] = str(db_port)
        if db_dialect is not None:
            container_env["DATABASE_DIALECT"] = db_dialect

        # Superset redis connection
        redis_host = self.get_redis_host()
        redis_port = self.get_redis_port()
        redis_driver = self.get_redis_driver()
        if self.args.redis_app is not None and isinstance(self.args.redis_app, DbApp):
            logger.debug(
                f"Reading redis connection details from: {self.args.redis_app.name}"
            )
            if redis_host is None:
                redis_host = self.args.redis_app.get_db_host_k8s()
            if redis_port is None:
                redis_port = str(self.args.redis_app.get_db_port_k8s())
            if redis_driver is None:
                redis_driver = self.args.redis_app.get_db_driver()

        if redis_host is not None:
            container_env["REDIS_HOST"] = redis_host
        if redis_port is not None:
            container_env["REDIS_PORT"] = str(redis_port)
        if redis_driver is not None:
            container_env["REDIS_DRIVER"] = str(redis_driver)

        # Update the container env using env_file
        env_data_from_file = self.get_env_data()
        if env_data_from_file is not None:
            container_env.update(env_data_from_file)

        # Update the container env with user provided env, this overwrites any existing variables
        if self.args.env is not None and isinstance(self.args.env, dict):
            container_env.update(self.args.env)

        # Create a ConfigMap to set the container env variables which are not Secret
        container_env_cm = CreateConfigMap(
            cm_name=self.args.config_map_name or get_default_configmap_name(app_name),
            app_name=app_name,
            data=container_env,
        )
        # logger.debug(f"ConfigMap {container_env_cm.cm_name}: {container_env_cm.json(indent=2)}")
        config_maps.append(container_env_cm)

        # Create a Secret to set the container env variables which are Secret
        _secret_data = self.get_secret_data()
        if _secret_data is not None:
            container_env_secret = CreateSecret(
                secret_name=self.args.secret_name or get_default_secret_name(app_name),
                app_name=app_name,
                string_data=_secret_data,
            )
            secrets.append(container_env_secret)

        # Container Volumes
        # If mount_workspace=True first check if the workspace
        # should be mounted locally, otherwise
        # Create a Sidecar git-sync container and volume
        if self.args.mount_workspace:
            workspace_volume_name = (
                self.args.workspace_volume_name or get_default_volume_name(app_name)
            )

            if self.args.k8s_mount_local_workspace:
                workspace_root_path_str = str(self.workspace_root_path)
                workspace_root_container_path_str = str(workspace_root_container_path)
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

            elif self.args.create_git_sync_sidecar:
                workspace_mount_container_path_str = str(
                    self.args.workspace_mount_container_path
                )
                logger.debug(f"Creating EmptyDir")
                logger.debug(f"\tat: {workspace_mount_container_path_str}")
                workspace_volume = CreateVolume(
                    volume_name=workspace_volume_name,
                    app_name=app_name,
                    mount_path=workspace_mount_container_path_str,
                    volume_type=VolumeType.EMPTY_DIR,
                )
                volumes.append(workspace_volume)

                if self.args.git_sync_repo is not None:
                    git_sync_env = {
                        "GIT_SYNC_REPO": self.args.git_sync_repo,
                        "GIT_SYNC_ROOT": str(self.args.workspace_mount_container_path),
                        "GIT_SYNC_DEST": workspace_name,
                    }
                    if self.args.git_sync_branch is not None:
                        git_sync_env["GIT_SYNC_BRANCH"] = self.args.git_sync_branch
                    if self.args.git_sync_wait is not None:
                        git_sync_env["GIT_SYNC_WAIT"] = str(self.args.git_sync_wait)
                    git_sync_container = CreateContainer(
                        container_name="git-sync-workspaces",
                        app_name=app_name,
                        image_name="k8s.gcr.io/git-sync",
                        image_tag="v3.1.1",
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

        # Create the ports to open
        # if open_container_port = True
        if self.args.open_container_port:
            container_port = CreatePort(
                name=self.args.container_port_name,
                container_port=self.args.container_port,
            )
            ports.append(container_port)

        # if open_app_port = True
        # 1. Set the app_port in the container env
        # 2. Open the superset app port
        app_port: Optional[CreatePort] = None
        if self.args.open_app_port:
            # Set the app port in the container env
            if container_env_cm.data is not None:
                container_env_cm.data["SUPERSET_PORT"] = str(self.args.app_port)
            # Open the port
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

        # Create the container
        superset_container = CreateContainer(
            container_name=self.get_container_name(),
            app_name=app_name,
            image_name=self.args.image_name,
            image_tag=self.args.image_tag,
            # Equivalent to docker images CMD
            args=[self.args.command]
            if isinstance(self.args.command, str)
            else self.args.command,
            # Equivalent to docker images ENTRYPOINT
            command=[self.args.entrypoint]
            if isinstance(self.args.entrypoint, str)
            else self.args.entrypoint,
            image_pull_policy=self.args.image_pull_policy,
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
        containers.append(superset_container)

        # Set default container for kubectl commands
        # https://kubernetes.io/docs/reference/labels-annotations-taints/#kubectl-kubernetes-io-default-container
        pod_annotations = {
            "kubectl.kubernetes.io/default-container": superset_container.container_name
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

        # Create the deployment
        superset_deployment = CreateDeployment(
            deploy_name=self.args.deploy_name or get_default_deploy_name(app_name),
            pod_name=self.args.pod_name or get_default_pod_name(app_name),
            app_name=app_name,
            namespace=ns_name,
            service_account_name=sa_name,
            replicas=self.args.replicas,
            containers=containers,
            init_containers=init_containers if len(init_containers) > 0 else None,
            pod_node_selector=self.args.pod_node_selector,
            restart_policy=self.args.deploy_restart_policy,
            termination_grace_period_seconds=self.args.termination_grace_period_seconds,
            volumes=volumes if len(volumes) > 0 else None,
            labels=deploy_labels,
            pod_annotations=pod_annotations,
            topology_spread_key=self.args.topology_spread_key,
            topology_spread_max_skew=self.args.topology_spread_max_skew,
            topology_spread_when_unsatisfiable=self.args.topology_spread_when_unsatisfiable,
        )
        deployments.append(superset_deployment)

        # Create the services
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
                deployment=superset_deployment,
                ports=[app_port] if app_port else None,
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

    def init_k8s_resource_groups(self, k8s_build_context: K8sBuildContext) -> None:
        k8s_rg = self.get_k8s_rg(k8s_build_context)
        if k8s_rg is not None:
            if self.k8s_resource_groups is None:
                self.k8s_resource_groups = OrderedDict()
            self.k8s_resource_groups[k8s_rg.name] = k8s_rg

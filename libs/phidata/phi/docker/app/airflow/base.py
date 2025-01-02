from enum import Enum
from typing import Optional, Dict
from pathlib import Path

from phi.docker.app.base import DockerApp, ContainerContext  # noqa: F401
from phi.app.db_app import DbApp
from phi.utils.common import str_to_int
from phi.utils.log import logger


class AirflowLogsVolumeType(str, Enum):
    HostPath = "HostPath"
    EmptyDir = "EmptyDir"


class AirflowBase(DockerApp):
    # -*- App Name
    name: str = "airflow"

    # -*- Image Configuration
    image_name: str = "phidata/airflow"
    image_tag: str = "2.7.1"

    # -*- App Ports
    # Open a container port if open_port=True
    open_port: bool = False
    port_number: int = 8080

    # -*- Workspace Configuration
    # Path to the workspace directory inside the container
    workspace_dir_container_path: str = "/workspace"
    # Mount the workspace directory from host machine to the container
    mount_workspace: bool = False

    # -*- Airflow Configuration
    # airflow_env sets the AIRFLOW_ENV env var and can be used by
    # DAGs to separate dev/stg/prd code
    airflow_env: Optional[str] = None
    # Set the AIRFLOW_HOME env variable
    # Defaults to: /usr/local/airflow
    airflow_home: Optional[str] = None
    # Set the AIRFLOW__CORE__DAGS_FOLDER env variable to the workspace_root/{airflow_dags_dir}
    # By default, airflow_dags_dir is set to the "dags" folder in the workspace
    airflow_dags_dir: str = "dags"
    # Creates an airflow admin with username: admin, pass: admin
    create_airflow_admin_user: bool = False
    # Airflow Executor
    executor: str = "SequentialExecutor"

    # -*- Airflow Database Configuration
    # Set as True to wait for db before starting airflow
    wait_for_db: bool = False
    # Set as True to delay start by 60 seconds so that the db can be initialized
    wait_for_db_init: bool = False
    # Connect to the database using a DbApp
    db_app: Optional[DbApp] = None
    # Provide database connection details manually
    # db_user can be provided here or as the
    # DB_USER env var in the secrets_file
    db_user: Optional[str] = None
    # db_password can be provided here or as the
    # DB_PASSWORD env var in the secrets_file
    db_password: Optional[str] = None
    # db_database can be provided here or as the
    # DB_DATABASE env var in the secrets_file
    db_database: Optional[str] = None
    # db_host can be provided here or as the
    # DB_HOST env var in the secrets_file
    db_host: Optional[str] = None
    # db_port can be provided here or as the
    # DB_PORT env var in the secrets_file
    db_port: Optional[int] = None
    # db_driver can be provided here or as the
    # DB_DRIVER env var in the secrets_file
    db_driver: str = "postgresql+psycopg2"
    db_result_backend_driver: str = "db+postgresql"
    # Airflow db connections in the format { conn_id: conn_url }
    # converted to env var: AIRFLOW_CONN__conn_id = conn_url
    db_connections: Optional[Dict] = None
    # Set as True to migrate (initialize/upgrade) the airflow_db
    db_migrate: bool = False

    # -*- Airflow Redis Configuration
    # Set as True to wait for redis before starting airflow
    wait_for_redis: bool = False
    # Connect to redis using a DbApp
    redis_app: Optional[DbApp] = None
    # Provide redis connection details manually
    # redis_password can be provided here or as the
    # REDIS_PASSWORD env var in the secrets_file
    redis_password: Optional[str] = None
    # redis_schema can be provided here or as the
    # REDIS_SCHEMA env var in the secrets_file
    redis_schema: Optional[str] = None
    # redis_host can be provided here or as the
    # REDIS_HOST env var in the secrets_file
    redis_host: Optional[str] = None
    # redis_port can be provided here or as the
    # REDIS_PORT env var in the secrets_file
    redis_port: Optional[int] = None
    # redis_driver can be provided here or as the
    # REDIS_DRIVER env var in the secrets_file
    redis_driver: str = "redis"

    # -*- Logs Volume
    # Mount the logs directory on the container
    mount_logs: bool = True
    logs_volume_name: Optional[str] = None
    logs_volume_type: AirflowLogsVolumeType = AirflowLogsVolumeType.EmptyDir
    # Container path to mount the volume
    # - If logs_volume_container_path is provided, use that
    # - If logs_volume_container_path is None and airflow_home is set
    #       use airflow_home/logs
    # - If logs_volume_container_path is None and airflow_home is None
    #       use "/usr/local/airflow/logs"
    logs_volume_container_path: Optional[str] = None
    # Host path to mount the postgres volume
    # If volume_type = PostgresVolumeType.HOST_PATH
    logs_volume_host_path: Optional[Path] = None

    #  -*- Other args
    load_examples: bool = False

    def get_db_user(self) -> Optional[str]:
        return self.db_user or self.get_secret_from_file("DB_USER")

    def get_db_password(self) -> Optional[str]:
        return self.db_password or self.get_secret_from_file("DB_PASSWORD")

    def get_db_database(self) -> Optional[str]:
        return self.db_database or self.get_secret_from_file("DB_DATABASE")

    def get_db_driver(self) -> Optional[str]:
        return self.db_driver or self.get_secret_from_file("DB_DRIVER")

    def get_db_host(self) -> Optional[str]:
        return self.db_host or self.get_secret_from_file("DB_HOST")

    def get_db_port(self) -> Optional[int]:
        return self.db_port or str_to_int(self.get_secret_from_file("DB_PORT"))

    def get_redis_password(self) -> Optional[str]:
        return self.redis_password or self.get_secret_from_file("REDIS_PASSWORD")

    def get_redis_schema(self) -> Optional[str]:
        return self.redis_schema or self.get_secret_from_file("REDIS_SCHEMA")

    def get_redis_host(self) -> Optional[str]:
        return self.redis_host or self.get_secret_from_file("REDIS_HOST")

    def get_redis_port(self) -> Optional[int]:
        return self.redis_port or str_to_int(self.get_secret_from_file("REDIS_PORT"))

    def get_redis_driver(self) -> Optional[str]:
        return self.redis_driver or self.get_secret_from_file("REDIS_DRIVER")

    def get_airflow_home(self) -> str:
        return self.airflow_home or "/usr/local/airflow"

    def get_container_env(self, container_context: ContainerContext) -> Dict[str, str]:
        from phi.constants import (
            PHI_RUNTIME_ENV_VAR,
            PYTHONPATH_ENV_VAR,
            REQUIREMENTS_FILE_PATH_ENV_VAR,
            SCRIPTS_DIR_ENV_VAR,
            STORAGE_DIR_ENV_VAR,
            WORKFLOWS_DIR_ENV_VAR,
            WORKSPACE_DIR_ENV_VAR,
            WORKSPACE_ID_ENV_VAR,
            WORKSPACE_ROOT_ENV_VAR,
            INIT_AIRFLOW_ENV_VAR,
            AIRFLOW_ENV_ENV_VAR,
            AIRFLOW_HOME_ENV_VAR,
            AIRFLOW_DAGS_FOLDER_ENV_VAR,
            AIRFLOW_EXECUTOR_ENV_VAR,
            AIRFLOW_DB_CONN_URL_ENV_VAR,
        )

        # Container Environment
        container_env: Dict[str, str] = self.container_env or {}
        container_env.update(
            {
                "INSTALL_REQUIREMENTS": str(self.install_requirements),
                "MOUNT_RESOURCES": str(self.mount_resources),
                "MOUNT_WORKSPACE": str(self.mount_workspace),
                "PRINT_ENV_ON_LOAD": str(self.print_env_on_load),
                "RESOURCES_DIR_CONTAINER_PATH": str(self.resources_dir_container_path),
                PHI_RUNTIME_ENV_VAR: "docker",
                REQUIREMENTS_FILE_PATH_ENV_VAR: container_context.requirements_file or "",
                SCRIPTS_DIR_ENV_VAR: container_context.scripts_dir or "",
                STORAGE_DIR_ENV_VAR: container_context.storage_dir or "",
                WORKFLOWS_DIR_ENV_VAR: container_context.workflows_dir or "",
                WORKSPACE_DIR_ENV_VAR: container_context.workspace_dir or "",
                WORKSPACE_ROOT_ENV_VAR: container_context.workspace_root or "",
                # Env variables used by Airflow
                "MOUNT_LOGS": str(self.mount_logs),
                # INIT_AIRFLOW env var is required for phidata to generate DAGs from workflows
                INIT_AIRFLOW_ENV_VAR: str(True),
                "DB_MIGRATE": str(self.db_migrate),
                "WAIT_FOR_DB": str(self.wait_for_db),
                "WAIT_FOR_DB_INIT": str(self.wait_for_db_init),
                "WAIT_FOR_REDIS": str(self.wait_for_redis),
                "CREATE_AIRFLOW_ADMIN_USER": str(self.create_airflow_admin_user),
                AIRFLOW_EXECUTOR_ENV_VAR: str(self.executor),
                "AIRFLOW__CORE__LOAD_EXAMPLES": str(self.load_examples),
            }
        )

        try:
            if container_context.workspace_schema is not None:
                if container_context.workspace_schema.id_workspace is not None:
                    container_env[WORKSPACE_ID_ENV_VAR] = str(container_context.workspace_schema.id_workspace) or ""

        except Exception:
            pass

        if self.set_python_path:
            python_path = self.python_path
            if python_path is None:
                python_path = f"{container_context.workspace_root}:{self.get_airflow_home()}"
                if self.mount_resources and self.resources_dir_container_path is not None:
                    python_path = "{}:{}".format(python_path, self.resources_dir_container_path)
                if self.add_python_paths is not None:
                    python_path = "{}:{}".format(python_path, ":".join(self.add_python_paths))
            if python_path is not None:
                container_env[PYTHONPATH_ENV_VAR] = python_path

        # Set aws region and profile
        self.set_aws_env_vars(env_dict=container_env)

        # Set the AIRFLOW__CORE__DAGS_FOLDER
        container_env[AIRFLOW_DAGS_FOLDER_ENV_VAR] = f"{container_context.workspace_root}/{self.airflow_dags_dir}"

        # Set the AIRFLOW_ENV
        if self.airflow_env is not None:
            container_env[AIRFLOW_ENV_ENV_VAR] = self.airflow_env

        # Set the AIRFLOW_HOME
        if self.airflow_home is not None:
            container_env[AIRFLOW_HOME_ENV_VAR] = self.get_airflow_home()

        # Set the AIRFLOW__CONN_ variables
        if self.db_connections is not None:
            for conn_id, conn_url in self.db_connections.items():
                try:
                    af_conn_id = str("AIRFLOW_CONN_{}".format(conn_id)).upper()
                    container_env[af_conn_id] = conn_url
                except Exception as e:
                    logger.exception(e)
                    continue

        # Airflow db connection
        db_user = self.get_db_user()
        db_password = self.get_db_password()
        db_database = self.get_db_database()
        db_host = self.get_db_host()
        db_port = self.get_db_port()
        db_driver = self.get_db_driver()
        if self.db_app is not None and isinstance(self.db_app, DbApp):
            logger.debug(f"Reading db connection details from: {self.db_app.name}")
            if db_user is None:
                db_user = self.db_app.get_db_user()
            if db_password is None:
                db_password = self.db_app.get_db_password()
            if db_database is None:
                db_database = self.db_app.get_db_database()
            if db_host is None:
                db_host = self.db_app.get_db_host()
            if db_port is None:
                db_port = self.db_app.get_db_port()
            if db_driver is None:
                db_driver = self.db_app.get_db_driver()
        db_connection_url = f"{db_driver}://{db_user}:{db_password}@{db_host}:{db_port}/{db_database}"

        # Set the AIRFLOW__DATABASE__SQL_ALCHEMY_CONN
        if "None" not in db_connection_url:
            logger.debug(f"AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: {db_connection_url}")
            container_env[AIRFLOW_DB_CONN_URL_ENV_VAR] = db_connection_url

        # Set the database connection details in the container env
        if db_host is not None:
            container_env["DATABASE_HOST"] = db_host
        if db_port is not None:
            container_env["DATABASE_PORT"] = str(db_port)

        # Airflow redis connection
        if self.executor == "CeleryExecutor":
            # Airflow celery result backend
            celery_result_backend_driver = self.db_result_backend_driver or db_driver
            celery_result_backend_url = (
                f"{celery_result_backend_driver}://{db_user}:{db_password}@{db_host}:{db_port}/{db_database}"
            )
            # Set the AIRFLOW__CELERY__RESULT_BACKEND
            if "None" not in celery_result_backend_url:
                container_env["AIRFLOW__CELERY__RESULT_BACKEND"] = celery_result_backend_url

            # Airflow celery broker url
            _redis_pass = self.get_redis_password()
            redis_password = f"{_redis_pass}@" if _redis_pass else ""
            redis_schema = self.get_redis_schema()
            redis_host = self.get_redis_host()
            redis_port = self.get_redis_port()
            redis_driver = self.get_redis_driver()
            if self.redis_app is not None and isinstance(self.redis_app, DbApp):
                logger.debug(f"Reading redis connection details from: {self.redis_app.name}")
                if redis_password is None:
                    redis_password = self.redis_app.get_db_password()
                if redis_schema is None:
                    redis_schema = self.redis_app.get_db_database() or "0"
                if redis_host is None:
                    redis_host = self.redis_app.get_db_host()
                if redis_port is None:
                    redis_port = self.redis_app.get_db_port()
                if redis_driver is None:
                    redis_driver = self.redis_app.get_db_driver()

            # Set the AIRFLOW__CELERY__RESULT_BACKEND
            celery_broker_url = f"{redis_driver}://{redis_password}{redis_host}:{redis_port}/{redis_schema}"
            if "None" not in celery_broker_url:
                logger.debug(f"AIRFLOW__CELERY__BROKER_URL: {celery_broker_url}")
                container_env["AIRFLOW__CELERY__BROKER_URL"] = celery_broker_url

            # Set the redis connection details in the container env
            if redis_host is not None:
                container_env["REDIS_HOST"] = redis_host
            if redis_port is not None:
                container_env["REDIS_PORT"] = str(redis_port)

        # Update the container env using env_file
        env_data_from_file = self.get_env_file_data()
        if env_data_from_file is not None:
            container_env.update({k: str(v) for k, v in env_data_from_file.items() if v is not None})

        # Update the container env using secrets_file
        secret_data_from_file = self.get_secret_file_data()
        if secret_data_from_file is not None:
            container_env.update({k: str(v) for k, v in secret_data_from_file.items() if v is not None})

        # Update the container env with user provided env_vars
        # this overwrites any existing variables with the same key
        if self.env_vars is not None and isinstance(self.env_vars, dict):
            container_env.update({k: str(v) for k, v in self.env_vars.items() if v is not None})

        # logger.debug("Container Environment: {}".format(container_env))
        return container_env

    def get_container_volumes(self, container_context: ContainerContext) -> Dict[str, dict]:
        from phi.utils.defaults import get_default_volume_name

        container_volumes: Dict[str, dict] = super().get_container_volumes(container_context=container_context)

        # Create Logs Volume
        if self.mount_logs:
            logs_volume_container_path_str = self.logs_volume_container_path
            if logs_volume_container_path_str is None:
                logs_volume_container_path_str = f"{self.get_airflow_home()}/logs"

            if self.logs_volume_type == AirflowLogsVolumeType.EmptyDir:
                logs_volume_name = self.logs_volume_name
                if logs_volume_name is None:
                    logs_volume_name = get_default_volume_name(f"{self.get_app_name()}-logs")
                logger.debug(f"Mounting: {logs_volume_name}")
                logger.debug(f"\tto: {logs_volume_container_path_str}")
                container_volumes[logs_volume_name] = {
                    "bind": logs_volume_container_path_str,
                    "mode": "rw",
                }
            elif self.logs_volume_type == AirflowLogsVolumeType.HostPath:
                if self.logs_volume_host_path is not None:
                    logs_volume_host_path_str = str(self.logs_volume_host_path)
                    logger.debug(f"Mounting: {logs_volume_host_path_str}")
                    logger.debug(f"\tto: {logs_volume_container_path_str}")
                    container_volumes[logs_volume_host_path_str] = {
                        "bind": logs_volume_container_path_str,
                        "mode": "rw",
                    }
                else:
                    logger.error("Airflow: logs_volume_host_path is None")
            else:
                logger.error(f"{self.logs_volume_type.value} not supported")

        return container_volumes

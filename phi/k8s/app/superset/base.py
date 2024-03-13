from typing import Optional, Dict, List

from phi.app.db_app import DbApp
from phi.k8s.app.base import (
    K8sApp,
    AppVolumeType,  # noqa: F401
    ContainerContext,
    ServiceType,  # noqa: F401
    RestartPolicy,  # noqa: F401
    ImagePullPolicy,  # noqa: F401
)
from phi.utils.common import str_to_int
from phi.utils.log import logger


class SupersetBase(K8sApp):
    # -*- App Name
    name: str = "superset"

    # -*- Image Configuration
    image_name: str = "phidata/superset"
    image_tag: str = "2.1.1"

    # -*- App Ports
    # Open a container port if open_port=True
    open_port: bool = False
    port_number: int = 8088

    # -*- Python Configuration
    # Set the PYTHONPATH env var
    set_python_path: bool = True
    # Add paths to the PYTHONPATH env var
    add_python_paths: Optional[List[str]] = ["/app/pythonpath"]

    # -*- Workspace Configuration
    # Path to the parent directory of the workspace inside the container
    # When using git-sync, the git repo is cloned inside this directory
    #   i.e. this is the parent directory of the workspace
    workspace_parent_dir_container_path: str = "/usr/local/workspace"

    # -*- Superset Configuration
    # Set the SUPERSET_CONFIG_PATH env var
    superset_config_path: Optional[str] = None
    # Set the FLASK_ENV env var
    flask_env: str = "production"
    # Set the SUPERSET_ENV env var
    superset_env: str = "production"

    # -*- Superset Database Configuration
    wait_for_db: bool = False
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
    # DATABASE_PORT or DB_PORT env var in the secrets_file
    db_port: Optional[int] = None
    # db_driver can be provided here or as the
    # DATABASE_DIALECT or DB_DRIVER env var in the secrets_file
    db_driver: str = "postgresql+psycopg"

    # -*- Superset Redis Configuration
    wait_for_redis: bool = False
    # Connect to redis using a DbApp
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

    #  -*- Other args
    load_examples: bool = False

    def get_db_user(self) -> Optional[str]:
        return self.db_user or self.get_secret_from_file("DATABASE_USER") or self.get_secret_from_file("DB_USER")

    def get_db_password(self) -> Optional[str]:
        return (
            self.db_password
            or self.get_secret_from_file("DATABASE_PASSWORD")
            or self.get_secret_from_file("DB_PASSWORD")
        )

    def get_db_database(self) -> Optional[str]:
        return self.db_database or self.get_secret_from_file("DATABASE_DB") or self.get_secret_from_file("DB_DATABASE")

    def get_db_driver(self) -> Optional[str]:
        return self.db_driver or self.get_secret_from_file("DATABASE_DIALECT") or self.get_secret_from_file("DB_DRIVER")

    def get_db_host(self) -> Optional[str]:
        return self.db_host or self.get_secret_from_file("DATABASE_HOST") or self.get_secret_from_file("DB_HOST")

    def get_db_port(self) -> Optional[int]:
        return (
            self.db_port
            or str_to_int(self.get_secret_from_file("DATABASE_PORT"))
            or str_to_int(self.get_secret_from_file("DB_PORT"))
        )

    def get_redis_host(self) -> Optional[str]:
        return self.redis_host or self.get_secret_from_file("REDIS_HOST")

    def get_redis_port(self) -> Optional[int]:
        return self.redis_port or str_to_int(self.get_secret_from_file("REDIS_PORT"))

    def get_redis_driver(self) -> Optional[str]:
        return self.redis_driver or self.get_secret_from_file("REDIS_DRIVER")

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
                "WAIT_FOR_DB": str(self.wait_for_db),
                "WAIT_FOR_REDIS": str(self.wait_for_redis),
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

        # Set the SUPERSET_CONFIG_PATH
        if self.superset_config_path is not None:
            container_env["SUPERSET_CONFIG_PATH"] = self.superset_config_path

        # Set the FLASK_ENV
        if self.flask_env is not None:
            container_env["FLASK_ENV"] = self.flask_env

        # Set the SUPERSET_ENV
        if self.superset_env is not None:
            container_env["SUPERSET_ENV"] = self.superset_env

        # Set SUPERSET_LOAD_EXAMPLES
        if self.load_examples is not None:
            container_env["SUPERSET_LOAD_EXAMPLES"] = "yes"

        # Set SUPERSET_PORT
        if self.open_port and self.container_port is not None:
            container_env["SUPERSET_PORT"] = str(self.container_port)

        # Superset db connection
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

        if db_user is not None:
            container_env["DATABASE_USER"] = db_user
        if db_host is not None:
            container_env["DATABASE_HOST"] = db_host
        if db_port is not None:
            container_env["DATABASE_PORT"] = str(db_port)
        if db_database is not None:
            container_env["DATABASE_DB"] = db_database
        if db_driver is not None:
            container_env["DATABASE_DIALECT"] = db_driver
        # Ideally we don't want the password in the env
        # But the superset image expects it.
        if db_password is not None:
            container_env["DATABASE_PASSWORD"] = db_password

        # Superset redis connection
        redis_host = self.get_redis_host()
        redis_port = self.get_redis_port()
        redis_driver = self.get_redis_driver()
        if self.redis_app is not None and isinstance(self.redis_app, DbApp):
            logger.debug(f"Reading redis connection details from: {self.redis_app.name}")
            if redis_host is None:
                redis_host = self.redis_app.get_db_host()
            if redis_port is None:
                redis_port = self.redis_app.get_db_port()
            if redis_driver is None:
                redis_driver = self.redis_app.get_db_driver()

        if redis_host is not None:
            container_env["REDIS_HOST"] = redis_host
        if redis_port is not None:
            container_env["REDIS_PORT"] = str(redis_port)
        if redis_driver is not None:
            container_env["REDIS_DRIVER"] = str(redis_driver)

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

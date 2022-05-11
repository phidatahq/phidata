from pathlib import Path
from typing import Optional, Dict

from phidata.app.airflow.airflow_base import AirflowBase


class AirflowManager(AirflowBase):
    def __init__(
        self,
        name: str = "airflow-manager",
        version: str = "1",
        enabled: bool = True,
        # Image args,
        image_name: str = "phidata/airflow",
        image_tag: str = "2.3.0",
        entrypoint: str = "/manager.sh",
        command: Optional[str] = None,
        # Add env variables to container env,
        env: Optional[Dict[str, str]] = None,
        # Read env variables from a file in yaml format,
        env_file: Optional[Path] = None,
        # Read secrets from a file in yaml format,
        secrets_file: Optional[Path] = None,
        print_env_on_load: bool = True,
        init_airflow_db: bool = False,
        upgrade_airflow_db: bool = False,
        # Creates an airflow admin with username: admin, pass: admin
        # or reads details from secrets file
        create_airflow_admin_user: bool = False,
        # Additional args
        # If True, use cached resources
        # i.e. skip resource creation/deletion if active resources with the same name exist.
        use_cache: bool = True,
    ):
        env = env
        if env is None:
            env = {}
        env["INIT_AIRFLOW_DB"] = str(init_airflow_db)
        env["UPGRADE_AIRFLOW_DB"] = str(upgrade_airflow_db)

        super().__init__(
            name=name,
            version=version,
            enabled=enabled,
            image_name=image_name,
            image_tag=image_tag,
            entrypoint=entrypoint,
            command=command,
            env=env,
            env_file=env_file,
            secrets_file=secrets_file,
            create_airflow_admin_user=create_airflow_admin_user,
            print_env_on_load=print_env_on_load,
            use_cache=use_cache,
        )

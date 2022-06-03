from pathlib import Path
from typing import Optional, Dict, Any
from typing_extensions import Literal

from phidata.app.db import DbApp
from phidata.app.airflow.airflow_base import AirflowBase
from phidata.infra.k8s.enums.restart_policy import RestartPolicy


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
        # Creates an airflow admin with username: admin, pass: admin
        # or reads details from secrets file
        create_airflow_admin_user: bool = False,
        # Configure airflow db,
        # If init_airflow_db = True, initialize the airflow_db,
        init_airflow_db: bool = False,
        # Upgrade the airflow db
        upgrade_airflow_db: bool = False,
        wait_for_db: bool = True,
        # delay start by 60 seconds for the db to be initialized
        wait_for_db_init: bool = False,
        # Connect to database using DbApp,
        db_app: Optional[DbApp] = None,
        # Connect to database manually,
        db_user: Optional[str] = None,
        db_password: Optional[str] = None,
        db_schema: Optional[str] = None,
        db_host: Optional[str] = None,
        db_port: Optional[int] = None,
        db_driver: str = "postgresql+psycopg2",
        db_result_backend_driver: str = "db+postgresql",
        # Add env variables to container env,
        env: Optional[Dict[str, str]] = None,
        # Read env variables from a file in yaml format,
        env_file: Optional[Path] = None,
        # Read secrets from a file in yaml format,
        secrets_file: Optional[Path] = None,
        # Configure the deployment,
        deploy_name: Optional[str] = None,
        pod_name: Optional[str] = None,
        replicas: int = 1,
        pod_node_selector: Optional[Dict[str, str]] = None,
        restart_policy: RestartPolicy = RestartPolicy.ALWAYS,
        termination_grace_period_seconds: Optional[int] = None,
        # Add deployment labels
        deploy_labels: Optional[Dict[str, Any]] = None,
        # Determine how to spread the deployment across a topology
        # Key to spread the pods across
        topology_spread_key: Optional[str] = None,
        # The degree to which pods may be unevenly distributed
        topology_spread_max_skew: Optional[int] = None,
        # How to deal with a pod if it doesn't satisfy the spread constraint.
        topology_spread_when_unsatisfiable: Optional[
            Literal["DoNotSchedule", "ScheduleAnyway"]
        ] = None,
        print_env_on_load: bool = True,
        # Additional args
        # If True, use cached resources
        # i.e. skip resource creation/deletion if active resources with the same name exist.
        use_cache: bool = True,
    ):
        super().__init__(
            name=name,
            version=version,
            enabled=enabled,
            image_name=image_name,
            image_tag=image_tag,
            entrypoint=entrypoint,
            command=command,
            create_airflow_admin_user=create_airflow_admin_user,
            init_airflow_db=init_airflow_db,
            upgrade_airflow_db=upgrade_airflow_db,
            wait_for_db=wait_for_db,
            wait_for_db_init=wait_for_db_init,
            db_app=db_app,
            db_user=db_user,
            db_password=db_password,
            db_schema=db_schema,
            db_host=db_host,
            db_port=db_port,
            db_driver=db_driver,
            db_result_backend_driver=db_result_backend_driver,
            env=env,
            env_file=env_file,
            secrets_file=secrets_file,
            deploy_name=deploy_name,
            pod_name=pod_name,
            replicas=replicas,
            pod_node_selector=pod_node_selector,
            restart_policy=restart_policy,
            termination_grace_period_seconds=termination_grace_period_seconds,
            deploy_labels=deploy_labels,
            topology_spread_key=topology_spread_key,
            topology_spread_max_skew=topology_spread_max_skew,
            topology_spread_when_unsatisfiable=topology_spread_when_unsatisfiable,
            print_env_on_load=print_env_on_load,
            use_cache=use_cache,
        )

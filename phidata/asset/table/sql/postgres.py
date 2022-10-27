from typing import Optional, Any, Union, List, Dict

from sqlalchemy.engine import Engine, Connection

from phidata.app.db import DbApp
from phidata.asset.table.sql import SqlTable, SqlTableArgs, SqlType
from phidata.task import Task
from phidata.check import Check
from phidata.utils.log import logger


class PostgresTable(SqlTable):
    def __init__(
        self,
        # Table Name,
        name: Optional[str] = None,
        # Table schema,
        db_schema: Optional[str] = None,
        # sqlalchemy.engine.(Engine or Connection),
        # Using SQLAlchemy makes it possible to use any DB supported by that library.,
        # NOTE: db_engine is required but can be derived using other args.,
        db_engine: Optional[Union[Engine, Connection]] = None,
        # a db_conn_url can be used to create the sqlalchemy.engine.Engine object,
        db_conn_url: Optional[str] = None,
        # airflow connection_id used for running workflows on airflow,
        airflow_conn_id: Optional[str] = None,
        # Phidata DbApp to connect to the database,
        db_app: Optional[DbApp] = None,
        # Checks to run before loading the table,
        pre_checks: Optional[List[Check]] = None,
        # List of tasks to create the table
        create_tasks: Optional[List[Task]] = None,
        # Checks to run after loading the table,
        post_checks: Optional[List[Check]] = None,
        # List of tasks to update the table,
        update_tasks: Optional[List[Task]] = None,
        # List of tasks to delete the table,
        delete_tasks: Optional[List[Task]] = None,
        # Control which environment the table is created in
        env: Optional[str] = None,
        # Dev Args,
        dev_name: Optional[str] = None,
        dev_env: Optional[Dict[str, Any]] = None,
        seed_dev_tasks: Optional[List[Task]] = None,
        dev_stg_swap_tasks: Optional[List[Task]] = None,
        # Staging Args,
        stg_name: Optional[str] = None,
        stg_env: Optional[Dict[str, Any]] = None,
        seed_stg_tasks: Optional[List[Task]] = None,
        stg_prd_swap_tasks: Optional[List[Task]] = None,
        # Production Args,
        prd_name: Optional[str] = None,
        prd_env: Optional[Dict[str, Any]] = None,
        cached_db_engine: Optional[Union[Engine, Connection]] = None,
        version: Optional[str] = None,
        enabled: bool = True,
        **kwargs,
    ) -> None:
        super().__init__()
        try:
            self.args: SqlTableArgs = SqlTableArgs(
                name=name,
                sql_type=SqlType.POSTGRES,
                db_schema=db_schema,
                db_engine=db_engine,
                db_conn_url=db_conn_url,
                airflow_conn_id=airflow_conn_id,
                db_app=db_app,
                pre_checks=pre_checks,
                create_tasks=create_tasks,
                post_checks=post_checks,
                update_tasks=update_tasks,
                delete_tasks=delete_tasks,
                env=env,
                dev_name=dev_name,
                dev_env=dev_env,
                seed_dev_tasks=seed_dev_tasks,
                dev_stg_swap_tasks=dev_stg_swap_tasks,
                stg_name=stg_name,
                stg_env=stg_env,
                seed_stg_tasks=seed_stg_tasks,
                stg_prd_swap_tasks=stg_prd_swap_tasks,
                prd_name=prd_name,
                prd_env=prd_env,
                cached_db_engine=cached_db_engine,
                version=version,
                enabled=enabled,
                **kwargs,
            )
        except Exception as e:
            logger.error(f"Args for {self.name} are not valid")
            raise

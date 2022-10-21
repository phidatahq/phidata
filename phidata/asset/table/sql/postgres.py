from typing import Optional, Any, Union, List

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
        # Checks to run after loading the table,
        post_checks: Optional[List[Check]] = None,
        # Dev Table Name,
        dev_table_name: Optional[str] = None,
        dev_checks: Optional[List[Check]] = None,
        dev_stg_swap_tasks: Optional[List[Task]] = None,
        # Staging Table Name,
        stg_table_name: Optional[str] = None,
        stg_checks: Optional[List[Check]] = None,
        stg_prd_swap_tasks: Optional[List[Task]] = None,
        # Production Table Name,
        prd_table_name: Optional[str] = None,
        prd_checks: Optional[List[Check]] = None,
        cached_db_engine: Optional[Union[Engine, Connection]] = None,
        version: Optional[str] = None,
        enabled: bool = True,
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
                post_checks=post_checks,
                dev_table_name=dev_table_name,
                dev_checks=dev_checks,
                dev_stg_swap_tasks=dev_stg_swap_tasks,
                stg_table_name=stg_table_name,
                stg_checks=stg_checks,
                stg_prd_swap_tasks=stg_prd_swap_tasks,
                prd_table_name=prd_table_name,
                prd_checks=prd_checks,
                cached_db_engine=cached_db_engine,
                version=version,
                enabled=enabled,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

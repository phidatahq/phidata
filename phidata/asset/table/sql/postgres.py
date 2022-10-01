from typing import Optional, Union, Sequence
from typing_extensions import Literal

from sqlalchemy.engine import Engine, Connection

from phidata.app.db import DbApp
from phidata.asset.table.sql import SqlTable, SqlTableArgs, SqlType
from phidata.utils.cli_console import print_info, print_error


class PostgresTableArgs(SqlTableArgs):
    sql_type: SqlType = SqlType.POSTGRES


class PostgresTable(SqlTable):
    def __init__(
        self,
        name: str,
        db_schema: Optional[str] = None,
        db_engine: Optional[Union[Engine, Connection]] = None,
        db_conn_url: Optional[str] = None,
        airflow_conn_id: Optional[str] = None,
        db_app: Optional[DbApp] = None,
        version: Optional[str] = None,
        enabled: bool = True,
    ) -> None:
        super().__init__()
        try:
            self.args: PostgresTableArgs = PostgresTableArgs(
                name=name,
                sql_type=SqlType.POSTGRES,
                db_schema=db_schema,
                db_engine=db_engine,
                db_conn_url=db_conn_url,
                airflow_conn_id=airflow_conn_id,
                db_app=db_app,
                version=version,
                enabled=enabled,
            )
        except Exception as e:
            print_error(f"Args for {self.__class__.__name__} are not valid")
            raise

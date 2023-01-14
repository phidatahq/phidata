from typing import Optional, Any, Union

from sqlalchemy.engine import Engine, Connection

from phidata.table.sql.sql_table import SqlTable, SqlTableFormat


class PostgresTable(SqlTable):
    def __init__(
        self,
        # Table Name: required
        name: str,
        # SQLModel for this table: required
        data_model: Any,
        # Database for the table (eg: "public" on postgres)
        database: Optional[str] = None,
        # -*- Table Connection
        # sqlalchemy.engine.(Engine or Connection)
        # Using SQLAlchemy makes it possible to use any DB supported by that library.
        # NOTE: db_engine is required but can be derived using other args.
        db_engine: Optional[Union[Engine, Connection]] = None,
        # a db_conn_url can be used to create the sqlalchemy.engine.Engine object
        db_conn_url: Optional[str] = None,
        # airflow connection_id used for running workflows on airflow
        airflow_conn_id: Optional[str] = None,
        # Phidata DbApp to connect to the database,
        db_app: Optional[Any] = None,
        echo: bool = False,
        cached_db_engine: Optional[Union[Engine, Connection]] = None,
        version: Optional[str] = None,
        enabled: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(
            name=name,
            data_model=data_model,
            table_format=SqlTableFormat.POSTGRES,
            database=database,
            db_engine=db_engine,
            db_conn_url=db_conn_url,
            airflow_conn_id=airflow_conn_id,
            db_app=db_app,
            echo=echo,
            cached_db_engine=cached_db_engine,
            version=version,
            enabled=enabled,
            **kwargs,
        )

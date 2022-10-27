from typing import Optional, Any, Union, List, Dict
from typing_extensions import Literal

from sqlalchemy.engine import Engine, Connection
from sqlalchemy.exc import ResourceClosedError

from phidata.asset import DataAsset, DataAssetArgs
from phidata.task import Task
from phidata.check import Check

from phidata.utils.enums import ExtendedEnum
from phidata.utils.log import logger
from phidata.types.phidata_runtime import PhidataRuntimeType


class SqlType(ExtendedEnum):
    POSTGRES = "POSTGRES"


class SqlTableArgs(DataAssetArgs):
    # Table Name
    name: str
    # Type of SQL table
    sql_type: SqlType
    # Table schema
    db_schema: Optional[str] = None
    # sqlalchemy.engine.(Engine or Connection)
    # Using SQLAlchemy makes it possible to use any DB supported by that library.
    # NOTE: db_engine is required but can be derived using other args.
    db_engine: Optional[Union[Engine, Connection]] = None
    # a db_conn_url can be used to create the sqlalchemy.engine.Engine object
    db_conn_url: Optional[str] = None
    # airflow connection_id used for running workflows on airflow
    airflow_conn_id: Optional[str] = None
    # Phidata DbApp to connect to the database
    db_app: Optional[Any] = None

    cached_db_engine: Optional[Union[Engine, Connection]] = None


class SqlTable(DataAsset):
    """Base Class for Sql tables"""

    def __init__(
        self,
        # Table Name,
        name: Optional[str] = None,
        # Type of SQL table,
        sql_type: Optional[SqlType] = None,
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
        db_app: Optional[Any] = None,
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
        self.args: Optional[SqlTableArgs] = None
        if name is not None and sql_type is not None:
            try:
                self.args = SqlTableArgs(
                    name=name,
                    sql_type=sql_type,
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

    @property
    def sql_type(self) -> Optional[SqlType]:
        return self.args.sql_type if self.args else None

    @sql_type.setter
    def sql_type(self, sql_type: SqlType) -> None:
        if self.args and sql_type:
            self.args.sql_type = sql_type

    @property
    def db_schema(self) -> Optional[str]:
        return self.args.db_schema if self.args else None

    @db_schema.setter
    def db_schema(self, db_schema: str) -> None:
        if self.args and db_schema:
            self.args.db_schema = db_schema

    @property
    def db_engine(self) -> Optional[Union[Engine, Connection]]:
        return self.args.db_engine if self.args else None

    @db_engine.setter
    def db_engine(self, db_engine: Union[Engine, Connection]) -> None:
        if self.args and db_engine:
            self.args.db_engine = db_engine

    @property
    def db_conn_url(self) -> Optional[str]:
        return self.args.db_conn_url if self.args else None

    @db_conn_url.setter
    def db_conn_url(self, db_conn_url: str) -> None:
        if self.args and db_conn_url:
            self.args.db_conn_url = db_conn_url

    @property
    def airflow_conn_id(self) -> Optional[str]:
        return self.args.airflow_conn_id if self.args else None

    @airflow_conn_id.setter
    def airflow_conn_id(self, airflow_conn_id: str) -> None:
        if self.args and airflow_conn_id:
            self.args.airflow_conn_id = airflow_conn_id

    @property
    def db_app(self) -> Optional[Any]:
        return self.args.db_app if self.args else None

    @db_app.setter
    def db_app(self, db_app: Any) -> None:
        if self.args and db_app:
            self.args.db_app = db_app

    @property
    def cached_db_engine(self) -> Optional[Union[Engine, Connection]]:
        return self.args.cached_db_engine if self.args else None

    @cached_db_engine.setter
    def cached_db_engine(self, cached_db_engine: Union[Engine, Connection]) -> None:
        if self.args and cached_db_engine:
            self.args.cached_db_engine = cached_db_engine

    def create_db_engine_using_conn_url(self) -> Optional[Union[Engine, Connection]]:
        # Create the SQLAlchemy engine using db_conn_url

        try:
            from sqlalchemy import create_engine

            # logger.info(f"Creating db_engine using db_conn_url: {self.db_conn_url}")
            db_engine = create_engine(self.db_conn_url)
            logger.debug(f"db_engine: {db_engine}")
            if isinstance(db_engine, tuple) and len(db_engine) > 0:
                self.db_engine = db_engine[0]
            else:
                self.db_engine = db_engine
            return self.db_engine
        except Exception as e:
            logger.error(f"Error creating db_engine using {self.db_conn_url}")
            logger.error(e)
            return None

    def create_db_engine_using_airflow_conn_id(
        self,
    ) -> Optional[Union[Engine, Connection]]:
        # Create the SQLAlchemy engine using airflow_conn_id

        try:
            from airflow.providers.postgres.hooks.postgres import PostgresHook

            logger.info(
                f"Creating db_engine using airflow_conn_id: {self.airflow_conn_id}"
            )
            if self.sql_type == SqlType.POSTGRES:
                pg_hook = PostgresHook(postgres_conn_id=self.airflow_conn_id)
                self.db_engine = pg_hook.get_sqlalchemy_engine()
            return self.db_engine
        except Exception as e:
            logger.error(f"Error creating db_engine using {self.airflow_conn_id}")
            logger.error(e)
            return None

    def create_db_engine_using_db_app(self) -> Optional[Union[Engine, Connection]]:
        # Create the SQLAlchemy engine using db_app

        if self.db_app is None:
            return None

        try:
            conn_url: Optional[str] = None

            phidata_runtime: Optional[PhidataRuntimeType] = self.phidata_runtime
            if phidata_runtime is None:
                conn_url = self.db_app.get_db_connection_url_local()
            if phidata_runtime == PhidataRuntimeType.local:
                conn_url = self.db_app.get_db_connection_url_local()
            if phidata_runtime == PhidataRuntimeType.docker:
                conn_url = self.db_app.get_db_connection_url_docker()
            if phidata_runtime == PhidataRuntimeType.kubernetes:
                conn_url = self.db_app.get_db_connection_url_k8s()

            if conn_url is None or "None" in conn_url:
                return None

            # Create the SQLAlchemy engine using conn_url
            from sqlalchemy import create_engine

            # logger.info(f"Creating db_engine using conn_url: {conn_url}")
            db_engine = create_engine(conn_url)
            logger.debug(f"db_engine: {db_engine}")
            if isinstance(db_engine, tuple) and len(db_engine) > 0:
                self.db_engine = db_engine[0]
            else:
                self.db_engine = db_engine
            return self.db_engine
        except Exception as e:
            logger.error(f"Error creating db_engine using {self.db_app}")
            logger.error(e)
            return None

    def create_db_engine(self) -> Optional[Union[Engine, Connection]]:
        if self.db_engine is not None:
            return self.db_engine

        if self.cached_db_engine is not None:
            return self.cached_db_engine

        if self.db_conn_url is not None:
            conn_url_db_engine = self.create_db_engine_using_conn_url()
            if conn_url_db_engine is not None:
                self.cached_db_engine = conn_url_db_engine
                return conn_url_db_engine

        if self.airflow_conn_id is not None:
            from phidata.airflow.airflow_installed import airflow_installed

            # Validate that airflow is installed on the machine
            if airflow_installed():
                airflow_conn_id_db_engine = (
                    self.create_db_engine_using_airflow_conn_id()
                )
                if airflow_conn_id_db_engine is not None:
                    self.cached_db_engine = airflow_conn_id_db_engine
                    return airflow_conn_id_db_engine

        if self.db_app is not None:
            db_app_db_engine = self.create_db_engine_using_db_app()
            if db_app_db_engine is not None:
                self.cached_db_engine = db_app_db_engine
                return db_app_db_engine

        return None

    ######################################################
    ## Write table
    ######################################################

    def write_pandas_df(
        self,
        df: Optional[Any] = None,
        # How to behave if the table already exists.
        # fail: Raise a ValueError.
        # replace: Drop the table before inserting new values.
        # append: Insert new values to the existing table.
        if_exists: Optional[Literal["fail", "replace", "append"]] = None,
        # Write DataFrame index as a column.
        # Uses index_label as the column name in the table.
        index: Optional[bool] = None,
        # Column label for index column(s).
        # If None is given (default) and index is True, then the index names are used.
        # A sequence should be given if the DataFrame uses MultiIndex.
        index_label: Optional[Union[str, List[str]]] = None,
        # Specify the number of rows in each batch to be written at a time.
        # By default, all rows will be written at once.
        chunksize: Optional[int] = None,
        # Create database if it does not exist.
        create_database: bool = False,
    ) -> bool:
        """
        Write DataFrame to table.
        """

        # SqlTable not yet initialized
        if self.args is None:
            return False

        # Check name is available
        if self.name is None:
            logger.error("SqlTable name not available")
            return False

        # Check engine is available
        db_engine = self.create_db_engine()
        if db_engine is None:
            logger.error("DbEngine not available")
            return False

        # write to table
        import pandas as pd

        if df is None or not isinstance(df, pd.DataFrame):
            logger.error("DataFrame invalid")
            return False

        rows_in_df = df.shape[0]
        logger.info(f"Writing {rows_in_df} rows to table: {self.name}")

        # create a dict of args provided
        not_null_args: Dict[str, Any] = {}
        if self.db_schema:
            not_null_args["schema"] = self.db_schema
        if if_exists:
            not_null_args["if_exists"] = if_exists
        if index:
            not_null_args["index"] = index
        if index_label:
            not_null_args["index_label"] = index_label
        if chunksize:
            not_null_args["chunksize"] = chunksize

        try:
            with db_engine.connect() as connection:
                if self.db_schema is not None and create_database:
                    logger.info(f"Creating database: {self.db_schema}")
                    # Create database if it does not exist
                    connection.execute(f"CREATE SCHEMA IF NOT EXISTS {self.db_schema}")

                df.to_sql(
                    name=self.name,
                    con=connection,
                    **not_null_args,
                )
                logger.info(f"--**-- Done")
            return True
        except Exception:
            logger.error("Could not write table: {}".format(self.name))
            raise

    ######################################################
    ## Read table
    ######################################################

    def read_pandas_df(
        self,
        index_col: Optional[Union[str, List[str]]] = None,
        coerce_float: bool = True,
        parse_dates: Optional[Union[List, Dict]] = None,
        columns: Optional[List[str]] = None,
        chunksize: Optional[int] = None,
    ) -> Optional[Any]:
        """
        Read table into a DataFrame.

        Args:
            index_col : str or list of str, optional, default: None
                Column(s) to set as index(MultiIndex).
            coerce_float : bool, default True
                Attempts to convert values of non-string, non-numeric objects (like
                decimal.Decimal) to floating point. Can result in loss of Precision.
            parse_dates : list or dict, default None
                - List of column names to parse as dates.
                - Dict of ``{column_name: format string}`` where format string is
                strftime compatible in case of parsing string times or is one of
                (D, s, ns, ms, us) in case of parsing integer timestamps.
                - Dict of ``{column_name: arg dict}``, where the arg dict corresponds
                to the keyword arguments of :func:`pandas.to_datetime`
                Especially useful with databases without native Datetime support,
                such as SQLite.
            columns : list, default None
                List of column names to select from SQL table.
            chunksize : int, default None
                If specified, returns an iterator where `chunksize` is the number of
                rows to include in each chunk.

        Returns:
            DataFrame or Iterator[DataFrame]
            A SQL table is returned as two-dimensional data structure with labeled
            axes.
        """

        # SqlTable not yet initialized
        if self.args is None:
            return False

        # Check engine is available
        db_engine = self.create_db_engine()
        if db_engine is None:
            logger.error("DbEngine not available")
            return False

        # read sql table
        import pandas as pd

        logger.info("Reading table: {}".format(self.name))

        # create a dict of args provided
        not_null_args: Dict[str, Any] = {}
        if self.db_schema:
            not_null_args["schema"] = self.db_schema
        if index_col:
            not_null_args["index_col"] = index_col
        if coerce_float:
            not_null_args["coerce_float"] = coerce_float
        if parse_dates:
            not_null_args["parse_dates"] = parse_dates
        if columns:
            not_null_args["columns"] = columns
        if chunksize:
            not_null_args["chunksize"] = chunksize

        try:
            with db_engine.connect() as connection:
                result_df = pd.read_sql_table(
                    table_name=self.name,
                    con=connection,
                    **not_null_args,
                )
            return result_df
        except Exception:
            logger.error(f"Could not read table: {self.name}")
            raise

    def run_sql_query(
        self,
        sql_query: str,
        index_col: Optional[Union[str, List[str]]] = None,
        coerce_float: bool = True,
        parse_dates: Optional[Union[List, Dict]] = None,
        columns: Optional[List[str]] = None,
        chunksize: Optional[int] = None,
    ) -> Optional[Any]:
        """
        Run SQL query using pandas.read_sql()

        Args:
            index_col : str or list of str, optional, default: None
                Column(s) to set as index(MultiIndex).
            coerce_float : bool, default True
                Attempts to convert values of non-string, non-numeric objects (like
                decimal.Decimal) to floating point. Can result in loss of Precision.
            parse_dates : list or dict, default None
                - List of column names to parse as dates.
                - Dict of ``{column_name: format string}`` where format string is
                strftime compatible in case of parsing string times or is one of
                (D, s, ns, ms, us) in case of parsing integer timestamps.
                - Dict of ``{column_name: arg dict}``, where the arg dict corresponds
                to the keyword arguments of :func:`pandas.to_datetime`
                Especially useful with databases without native Datetime support,
                such as SQLite.
            columns : list, default None
                List of column names to select from SQL table.
            chunksize : int, default None
                If specified, returns an iterator where `chunksize` is the number of
                rows to include in each chunk.

        Returns:
            DataFrame or Iterator[DataFrame]
            A SQL table is returned as two-dimensional data structure with labeled
            axes.
        """

        # SqlTable not yet initialized
        if self.args is None:
            return None

        # Check engine is available
        db_engine = self.create_db_engine()
        if db_engine is None:
            logger.error("DbEngine not available")
            return False

        # run sql query
        import pandas as pd

        logger.info("Running Query:\n{}".format(sql_query))

        # create a dict of args provided
        not_null_args: Dict[str, Any] = {}
        if self.db_schema:
            not_null_args["schema"] = self.db_schema
        if index_col:
            not_null_args["index_col"] = index_col
        if coerce_float:
            not_null_args["coerce_float"] = coerce_float
        if parse_dates:
            not_null_args["parse_dates"] = parse_dates
        if columns:
            not_null_args["columns"] = columns
        if chunksize:
            not_null_args["chunksize"] = chunksize

        try:
            with db_engine.connect() as connection:
                result_df = pd.read_sql(
                    sql=sql_query,
                    con=connection,
                    **not_null_args,
                )
            return result_df
        except ResourceClosedError as rce:
            logger.info(
                f"The result object was closed automatically, returning no rows."
            )
        # except Exception as e:
        #     logger.error(f"Sql query failed: {e}")
        return None

    ######################################################
    ## Drop table
    ######################################################

    def _delete(self) -> bool:
        try:
            result = self.run_sql_query(f"DROP TABLE {self.name};")
        except Exception as e:
            logger.error(f"Drop table failed: {e}")
        return True

from typing import Optional, Any, Union, List, Dict
from typing_extensions import Literal

from sqlalchemy.engine import Engine, Connection
from sqlalchemy.exc import ResourceClosedError

from phidata.asset.data_asset import DataAsset, DataAssetArgs
from phidata.checks.check import Check
from phidata.utils.enums import ExtendedEnum
from phidata.utils.log import logger
from phidata.types.phidata_runtime import PhidataRuntimeType


class SqlTableFormat(ExtendedEnum):
    POSTGRES = "POSTGRES"


class SqlTableArgs(DataAssetArgs):
    # Table Name
    name: str
    # Table Format
    table_format: SqlTableFormat
    # Database for the table (eg: "public" on postgres)
    database: Optional[str] = None

    # -*- Table Connection
    # sqlalchemy.engine.(Engine or Connection)
    # Using SQLAlchemy makes it possible to use any DB supported by that library.
    # NOTE: db_engine is required but can be derived using
    # db_conn_url, airflow_conn_id or db_app
    db_engine: Optional[Union[Engine, Connection]] = None
    # a db_conn_url can be used to create the sqlalchemy.engine.Engine object
    db_conn_url: Optional[str] = None
    # airflow connection_id used for running workflows on airflow
    airflow_conn_id: Optional[str] = None
    # Phidata DbApp to connect to the database
    db_app: Optional[Any] = None

    echo: bool = False
    cached_db_engine: Optional[Union[Engine, Connection]] = None


class SqlTable(DataAsset):
    """Base Class for Sql tables"""

    def __init__(
        self,
        # Table Name: required
        name: str,
        # Table Format: required
        table_format: SqlTableFormat,
        # Database for the table (eg: "public" on postgres)
        database: Optional[str] = None,
        # DataModel for this table (SQLModel object)
        data_model: Optional[Any] = None,
        # Checks to run before reading from disk
        read_checks: Optional[List[Check]] = None,
        # Checks to run before writing to disk
        write_checks: Optional[List[Check]] = None,
        # -*- Table Connection
        # sqlalchemy.engine.(Engine or Connection)
        # Using SQLAlchemy makes it possible to use any DB supported by that library.
        # NOTE: db_engine is required but can be derived using
        # db_conn_url, airflow_conn_id or db_app
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
        super().__init__()
        try:
            self.args: SqlTableArgs = SqlTableArgs(
                name=name,
                table_format=table_format,
                database=database,
                data_model=data_model,
                read_checks=read_checks,
                write_checks=write_checks,
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
        except Exception as e:
            logger.error(f"Args for {self.name} are not valid")
            raise

    @property
    def table_format(self) -> Optional[SqlTableFormat]:
        return self.args.table_format if self.args else None

    @table_format.setter
    def table_format(self, table_format: SqlTableFormat) -> None:
        if self.args and table_format:
            self.args.table_format = table_format

    @property
    def database(self) -> Optional[str]:
        return self.args.database if self.args else None

    @database.setter
    def database(self, database: str) -> None:
        if self.args and database:
            self.args.database = database

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
    def echo(self) -> bool:
        return self.args.echo if self.args else False

    @echo.setter
    def echo(self, echo: bool) -> None:
        if self.args and echo:
            self.args.echo = echo

    @property
    def cached_db_engine(self) -> Optional[Union[Engine, Connection]]:
        return self.args.cached_db_engine if self.args else None

    @cached_db_engine.setter
    def cached_db_engine(self, cached_db_engine: Union[Engine, Connection]) -> None:
        if self.args and cached_db_engine:
            self.args.cached_db_engine = cached_db_engine

    def create_db_engine_using_conn_url(self) -> Optional[Union[Engine, Connection]]:
        # Create the SQLAlchemy engine using db_conn_url

        if self.db_conn_url is None:
            return None

        # Validate sqlmodel is installed
        try:
            from sqlmodel import create_engine  # type: ignore
        except ImportError as ie:
            raise Exception("SQLModel not installed") from ie

        try:
            logger.info("Creating db_engine using db_conn_url")
            db_engine = create_engine(self.db_conn_url, echo=self.echo)
            logger.debug(f"Created db_engine: {db_engine}")
            if isinstance(db_engine, tuple) and len(db_engine) > 0:
                self.db_engine = db_engine[0]
            else:
                self.db_engine = db_engine
            return self.db_engine
        except Exception as e:
            logger.error("Error creating db_engine using db_conn_url")
            logger.error(e)
            return None

    def create_db_engine_using_airflow_conn_id(
        self,
    ) -> Optional[Union[Engine, Connection]]:
        # Create the SQLAlchemy engine using airflow_conn_id

        # Validate airflow is installed
        try:
            from airflow.providers.postgres.hooks.postgres import PostgresHook
        except ImportError as ie:
            raise Exception("Airflow not installed") from ie

        try:
            logger.info(
                f"Creating db_engine using airflow_conn_id: {self.airflow_conn_id}"
            )
            if self.table_format == SqlTableFormat.POSTGRES:
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

            # Validate sqlmodel is installed
            try:
                from sqlmodel import create_engine
            except ImportError as ie:
                raise Exception("SQLModel not installed") from ie

            # Create the SQLAlchemy engine
            logger.debug("Creating db_engine using db_app")
            db_engine = create_engine(conn_url, echo=self.echo)
            logger.debug(f"Created db_engine: {db_engine}")
            if isinstance(db_engine, tuple) and len(db_engine) > 0:
                self.db_engine = db_engine[0]
            else:
                self.db_engine = db_engine
            return self.db_engine
        except Exception as e:
            logger.error("Error creating db_engine using db_app")
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
    ## Validate data asset
    ######################################################

    def is_valid(self) -> bool:
        return True

    ######################################################
    ## Build data asset
    ######################################################

    def build(self) -> bool:
        logger.debug(f"@build not defined for {self.name}")
        return False

    ######################################################
    ## Write DataAsset
    ######################################################

    def write_table(
        self,
        # A pyarrow.Table
        table: Optional[Any] = None,
        # -*- Number of rows that are processed per thread.
        # By default, all rows will be written at once.
        batch_size: int = 1024,
        # -*- Create the table if it does not exist
        create_table: bool = False,
        # -*- Create database if it does not exist.
        create_database: bool = False,
        **kwargs,
    ) -> bool:
        """
        Write pyarrow.Table to table.

        https://arrow.apache.org/docs/python/generated/pyarrow.Table.html#pyarrow.Table
        """
        # Validate pyarrow is installed
        try:
            import pyarrow as pa
        except ImportError as ie:
            raise Exception(
                f"PyArrow not installed. Please install with `pip install pyarrow`"
            ) from ie

        # Validate sqlmodel is installed
        try:
            from sqlmodel import SQLModel, Session
        except ImportError as ie:
            logger.error(f"SQLModel not installed: {ie}")
            return False

        # Validate table
        if table is None or not isinstance(table, pa.Table):
            logger.error("Table invalid")
            return False

        # Update batch_size
        if batch_size < 1:
            batch_size = 1

        # Check engine is available
        db_engine = self.create_db_engine()
        if db_engine is None:
            logger.error("DbEngine invalid")
            return False

        # Validate sql_model
        if self.data_model is None:
            logger.error("SQLModel invalid")
            return False
        sql_model: SQLModel = self.data_model

        # Validate the Table object
        # https://docs.sqlalchemy.org/en/14/core/metadata.html#sqlalchemy.schema.Table
        # https://docs.sqlalchemy.org/en/14/orm/declarative_tables.html#accessing-table-and-metadata
        sql_model_table = sql_model.__table__  # type: ignore
        if sql_model_table is None:
            logger.error("SQLModel table invalid")
            return False

        # Validate table columns match sql_model columns
        table_columns = table.column_names
        sql_model_columns = sql_model.__fields__.keys()
        if not set(table_columns).issubset(set(sql_model_columns)):
            logger.error("Table columns do not match SQLModel columns")
            logger.debug(f"Table columns: {set(table_columns)}")
            logger.debug(f"SQLModel columns: {set(sql_model_columns)}")
            return False

        # Load table
        rows_in_table = table.num_rows
        logger.info(f"Writing {rows_in_table} rows to table: {self.name}")
        try:
            # Create database if it does not exist
            # TODO: This is not working
            if self.database is not None and create_database:
                with db_engine.connect() as connection:
                    connection.execute(f"CREATE SCHEMA IF NOT EXISTS {self.database}")
                    logger.info(f"Schema created: {self.database}")

            # Create session
            session = Session(db_engine)

            # Create table if it does not exist
            if create_table:
                sql_model_table.create(db_engine, checkfirst=True)

            # Write DataFrame to table
            rows_to_commit = 0
            if rows_in_table > 0:
                batches: List[pa.RecordBatch] = table.to_batches(
                    max_chunksize=batch_size
                )
                for batch in batches:
                    batch_rows = batch.to_pylist()

                    for row in batch_rows:
                        # logger.debug(f"Building row: {row}")

                        # Create SQLModel for row
                        row_model = sql_model(**row)  # type: ignore # noqa
                        # logger.debug(f"Writing row: {row_model}")
                        # Add to session
                        session.add(row_model)
                        rows_to_commit += 1
                        if rows_to_commit >= batch_size:
                            # Commit session
                            session.commit()
                            logger.info(f"Commit {rows_to_commit} rows")
                            rows_to_commit = 0
                if rows_to_commit > 0:
                    # Final Commit
                    session.commit()
                    logger.info(f"Commit {rows_to_commit} rows")
            logger.info(f"--**-- Done")
            return True
        except Exception:
            logger.error("Could not write table: {}".format(self.name))
            raise

    def write_polars_df(
        self,
        # A polars DataFrame
        df: Optional[Any] = None,
        # -*- Number of rows that are processed per thread.
        # By default, all rows will be written at once.
        batch_size: int = 1024,
        # -*- Create the table if it does not exist
        create_table: bool = False,
        # -*- Create database if it does not exist.
        create_database: bool = False,
        **kwargs,
    ) -> bool:
        """
        Write DataFrame to table.
        """
        # Validate polars is installed
        try:
            import polars as pl  # type: ignore
        except ImportError as ie:
            logger.error(f"Polars not installed: {ie}")
            return False

        # Validate sqlmodel is installed
        try:
            from sqlmodel import SQLModel, Session
        except ImportError as ie:
            logger.error(f"SQLModel not installed: {ie}")
            return False

        # Validate df
        if df is None or not isinstance(df, pl.DataFrame):
            logger.error("DataFrame invalid")
            return False

        # Update batch_size
        if batch_size < 1:
            batch_size = 1

        # Check engine is available
        db_engine = self.create_db_engine()
        if db_engine is None:
            logger.error("DbEngine invalid")
            return False

        # Validate sql_model
        if self.data_model is None:
            logger.error("SQLModel invalid")
            return False
        sql_model: SQLModel = self.data_model

        # Validate the Table object
        # https://docs.sqlalchemy.org/en/14/core/metadata.html#sqlalchemy.schema.Table
        # https://docs.sqlalchemy.org/en/14/orm/declarative_tables.html#accessing-table-and-metadata
        sql_model_table = sql_model.__table__  # type: ignore
        if sql_model_table is None:
            logger.error("SQLModel table invalid")
            return False

        # Validate dataframe columns match sql_model columns
        df_columns = df.columns
        sql_model_columns = sql_model.__fields__.keys()
        if not set(df_columns).issubset(set(sql_model_columns)):
            logger.error("DataFrame columns do not match SQLModel columns")
            logger.debug(f"DataFrame columns: {set(df_columns)}")
            logger.debug(f"SQLModel columns: {set(sql_model_columns)}")
            return False

        # Load table
        rows_in_df = df.shape[0]
        logger.info(f"Writing {rows_in_df} rows to table: {self.name}")
        try:
            # Create database if it does not exist
            # TODO: This is not working
            if self.database is not None and create_database:
                with db_engine.connect() as connection:
                    connection.execute(f"CREATE SCHEMA IF NOT EXISTS {self.database}")
                    logger.info(f"Schema created: {self.database}")

            # Create session
            session = Session(db_engine)

            # Create table if it does not exist
            if create_table:
                sql_model_table.create(db_engine, checkfirst=True)

            # Write DataFrame to table
            rows_to_commit = 0
            if rows_in_df > 0:
                for df_row in df.rows():
                    row_dict = {}
                    for idx, col_name in enumerate(sql_model_columns, start=0):
                        row_dict[col_name] = df_row[idx]
                    # logger.debug(f"Building row: {row_dict}")

                    # Create SQLModel for row
                    row_model = sql_model(**row_dict)  # type: ignore # noqa
                    # logger.debug(f"Writing row: {row_model}")
                    # Add to session
                    session.add(row_model)
                    rows_to_commit += 1
                    if rows_to_commit >= batch_size:
                        # Commit session
                        session.commit()
                        logger.info(f"Commit {rows_to_commit} rows")
                        rows_to_commit = 0
                if rows_to_commit > 0:
                    # Final Commit
                    session.commit()
                    logger.info(f"Commit {rows_to_commit} rows")
            logger.info(f"--**-- Done")
            return True
        except Exception:
            logger.error("Could not write table: {}".format(self.name))
            raise

    def write_pandas_df(
        self,
        df: Optional[Any] = None,
        # -*- Write DataFrame index as a column.
        # Uses index_label as the column name in the table.
        index: Optional[bool] = None,
        # -*- Column label for index column(s).
        # If None is given (default) and index is True, then the index names are used.
        # A sequence should be given if the DataFrame uses MultiIndex.
        index_label: Optional[Union[str, List[str]]] = None,
        # -*- Specify the number of rows in each batch to be written at a time.
        # By default, all rows will be written at once.
        chunksize: Optional[int] = None,
        # -*- Create database if it does not exist.
        create_database: bool = False,
        # -*- How to behave if the table already exists.
        # fail: Raise a ValueError.
        # replace: Drop the table before inserting new values.
        # append: Insert new values to the existing table.
        if_exists: Optional[Literal["fail", "replace", "append"]] = None,
        **kwargs,
    ) -> bool:
        """
        Write DataFrame to table.
        """
        # Validate pandas is installed
        try:
            import pandas as pd
        except ImportError:
            logger.error("Pandas not installed")
            return False

        # Validate df
        if df is None or not isinstance(df, pd.DataFrame):
            logger.error("DataFrame invalid")
            return False

        # Check engine is available
        db_engine = self.create_db_engine()
        if db_engine is None:
            logger.error("DbEngine not available")
            return False

        rows_in_df = df.shape[0]
        logger.info(f"Writing {rows_in_df} rows to table: {self.name}")

        # create a dict of args provided
        not_null_args: Dict[str, Any] = {}
        if self.database:
            not_null_args["schema"] = self.database
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
                if self.database is not None and create_database:
                    logger.info(f"Creating database: {self.database}")
                    # Create database if it does not exist
                    connection.execute(f"CREATE SCHEMA IF NOT EXISTS {self.database}")

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
    ## Query table
    ######################################################

    def query(
        self,
        q: str,
    ) -> Optional[Any]:
        """
        Run SQL query using SqlAlchemy.
        """
        # Validate sqlalchemy is installed
        try:
            from sqlalchemy.sql import text
        except ImportError as ie:
            logger.error(f"SQLAlchemy not installed: {ie}")
            return False

        # Check engine is available
        db_engine = self.create_db_engine()
        if db_engine is None:
            logger.error("DbEngine not available")
            return False

        logger.info("Running Query:\n{}".format(q))
        try:
            with db_engine.begin() as connection:
                result = connection.execute(text(q))  # type: ignore
            return result
        except ResourceClosedError as rce:
            logger.info(
                f"The result object was closed automatically, returning no rows."
            )
        return None

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
            sql_query (str): SQL query to be executed.
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
        # Validate pandas is installed
        try:
            import pandas as pd
        except ImportError:
            logger.error("Pandas not installed")
            return False

        # Check engine is available
        db_engine = self.create_db_engine()
        if db_engine is None:
            logger.error("DbEngine not available")
            return False

        logger.info("Running Query:\n{}".format(sql_query))

        # create a dict of args provided
        not_null_args: Dict[str, Any] = {}
        if self.database:
            not_null_args["schema"] = self.database
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
    ## Create DataAsset
    ######################################################

    def _create(self, if_not_exists: bool = True) -> bool:
        # Validate sqlmodel is installed
        try:
            from sqlmodel import SQLModel
        except ImportError as ie:
            logger.error(f"SQLModel not installed: {ie}")
            return False

        # Check engine is available
        db_engine = self.create_db_engine()
        if db_engine is None:
            logger.error("DbEngine invalid")
            return False

        sql_model: SQLModel = self.data_model  # type: ignore
        sql_model_table = sql_model.__table__  # type: ignore
        if sql_model_table is None:
            logger.error("SQLModel table invalid")
            return False

        # https://docs.sqlalchemy.org/en/14/core/metadata.html#sqlalchemy.schema.Table.create
        logger.debug(f"Creating table: {sql_model_table.name}")
        sql_model_table.create(bind=db_engine, checkfirst=if_not_exists)
        return True

    def create(self, if_not_exists: bool = True) -> bool:
        # Step 1: Check if resource is valid
        if not self.is_valid():
            return False

        # Step 2: Skip resource creation if skip_create = True
        if self.skip_create:
            logger.debug(f"Skipping create: {self.name}")
            return True

        # Step 3: Create the resource
        self.resource_created = self._create(if_not_exists=if_not_exists)
        return self.resource_deleted

    ######################################################
    ## Read DataAsset
    ######################################################

    def read_table(self, **read_options) -> Optional[Any]:
        """
        Read pyarrow.Table from table.

        https://arrow.apache.org/docs/python/generated/pyarrow.Table.html#pyarrow.Table
        """
        # Validate pyarrow is installed
        try:
            import pyarrow as pa
            import pyarrow.dataset as ds
        except ImportError as ie:
            raise Exception(
                f"PyArrow not installed. Please install with `pip install pyarrow`"
            ) from ie
        return None

    def read_polars_df(self, **kwargs) -> Optional[Any]:
        logger.debug(f"@read_polars_df not defined for {self.name}")
        return False

    def read_pandas_df(
        self,
        index_col: Optional[Union[str, List[str]]] = None,
        coerce_float: bool = True,
        parse_dates: Optional[Union[List, Dict]] = None,
        columns: Optional[List[str]] = None,
        chunksize: Optional[int] = None,
        **kwargs,
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
        # Validate pandas is installed
        try:
            import pandas as pd
        except ImportError:
            logger.error("Pandas not installed")
            return False

        # Check engine is available
        db_engine = self.create_db_engine()
        if db_engine is None:
            logger.error("DbEngine not available")
            return False

        logger.info("Reading table: {}".format(self.name))

        # create a dict of args provided
        not_null_args: Dict[str, Any] = {}
        if self.database:
            not_null_args["schema"] = self.database
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

    def _read(self) -> Any:
        logger.error(f"@_read not defined for {self.name}")
        return False

    ######################################################
    ## Update DataAsset
    ######################################################

    def _update(self) -> Any:
        logger.error(f"@_update not defined for {self.name}")
        return False

    ######################################################
    ## Delete DataAsset
    ######################################################

    def _delete(self, where: Optional[str] = None) -> Any:
        return self.query(f"DELETE FROM {self.name} WHERE {where}")

    def delete(self, where: Optional[str] = None) -> bool:
        # Step 1: Check if resource is valid
        if not self.is_valid():
            return False

        # Step 2: Skip resource deletion if skip_delete = True
        if self.skip_delete:
            logger.debug(f"Skipping delete: {self.name}")
            return True

        # Step 3: Delete the resource
        self.resource_deleted = self._delete(where=where)
        return self.resource_deleted

    def drop(self) -> Any:
        # Validate sqlmodel is installed
        try:
            from sqlmodel import SQLModel
        except ImportError as ie:
            logger.error(f"SQLModel not installed: {ie}")
            return False

        # Check engine is available
        db_engine = self.create_db_engine()
        if db_engine is None:
            logger.error("DbEngine invalid")
            return False

        sql_model: SQLModel = self.sql_model  # type: ignore
        sql_model_table = sql_model.__table__  # type: ignore
        if sql_model_table is None:
            logger.error("SQLModel table invalid")
            return False

        # https://docs.sqlalchemy.org/en/14/core/metadata.html#sqlalchemy.schema.Table.drop
        logger.debug(f"Dropping table: {sql_model_table.name}")
        sql_model_table.drop(bind=db_engine, checkfirst=True)
        return True

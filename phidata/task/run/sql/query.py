from typing import Optional, Literal, Union, List

from phidata.asset.table.sql import SqlTable
from phidata.utils.log import logger
from phidata.task import PythonTask, PythonTaskArgs


class RunSqlQueryArgs(PythonTaskArgs):
    query: str
    sql_table: SqlTable
    show_sample_data: bool = False
    load_result_to: Optional[SqlTable] = None
    # How to behave if the load_result_to already exists.
    # fail: Raise a ValueError.
    # replace: Drop the table before inserting new values.
    # append: Insert new values to the existing table.
    if_exists: Optional[Literal["fail", "replace", "append"]] = None
    # Write DataFrame index as a column.
    # Uses index_label as the column name in the table.
    index: Optional[bool] = None
    # Column label for index column(s).
    # If None is given (default) and index is True, then the index names are used.
    # A sequence should be given if the DataFrame uses MultiIndex.
    index_label: Optional[Union[str, List[str]]] = None
    # Specify the number of rows in each batch to be written at a time.
    # By default, all rows will be written at once.
    chunksize: Optional[int] = None
    create_db_engine_from_conn_id: bool = True


class RunSqlQuery(PythonTask):
    def __init__(
        self,
        query: str,
        sql_table: SqlTable,
        show_sample_data: bool = False,
        load_result_to: Optional[SqlTable] = None,
        if_exists: Optional[Literal["fail", "replace", "append"]] = None,
        index: Optional[bool] = None,
        index_label: Optional[Union[str, List[str]]] = None,
        chunksize: Optional[int] = None,
        name: str = "run_sql_query",
        task_id: Optional[str] = None,
        dag_id: Optional[str] = None,
        version: Optional[str] = None,
        enabled: bool = True,
    ):
        super().__init__()
        try:
            self.args: RunSqlQueryArgs = RunSqlQueryArgs(
                query=query,
                sql_table=sql_table,
                show_sample_data=show_sample_data,
                load_result_to=load_result_to,
                if_exists=if_exists,
                index=index,
                index_label=index_label,
                chunksize=chunksize,
                name=name,
                task_id=task_id,
                dag_id=dag_id,
                version=version,
                enabled=enabled,
                entrypoint=run_sql_query,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    @property
    def query(self) -> Optional[str]:
        return self.args.query

    @query.setter
    def query(self, query: str) -> None:
        if query is not None:
            self.args.query = query

    @property
    def sql_table(self) -> Optional[SqlTable]:
        return self.args.sql_table

    @sql_table.setter
    def sql_table(self, sql_table: SqlTable) -> None:
        if sql_table is not None:
            self.args.sql_table = sql_table


def run_sql_query_pandas(args: RunSqlQueryArgs) -> bool:

    import pandas as pd

    query: str = args.query
    sql_table: SqlTable = args.sql_table

    result_df: Optional[pd.DataFrame] = sql_table.run_sql_query(query)
    if result_df is None:
        logger.error("Result is empty")
        return False

    if args.show_sample_data:
        logger.info("Sample data:\n{}".format(result_df.head(5)))

    if args.load_result_to is not None:
        load_sql_table = args.load_result_to
        if not isinstance(load_sql_table, SqlTable):
            logger.error("load_result_to value not of type SqlTable")
            return False

        load_success = load_sql_table.write_pandas_df(
            df=result_df,
            if_exists=args.if_exists,
            index=args.index,
            index_label=args.index_label,
            chunksize=args.chunksize,
        )
        return load_success

    return True


def run_sql_query(**kwargs) -> bool:
    args: RunSqlQueryArgs = RunSqlQueryArgs(**kwargs)
    return run_sql_query_pandas(args)

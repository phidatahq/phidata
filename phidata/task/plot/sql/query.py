from typing import Optional, Any

from phidata.asset.table.sql import SqlTable
from phidata.utils.cli_console import print_info, print_error
from phidata.utils.log import logger
from phidata.task import PythonTask, PythonTaskArgs


class PlotSqlQueryArgs(PythonTaskArgs):
    query: str
    sql_table: SqlTable
    show_sample_data: bool = False
    create_db_engine_from_conn_id: bool = True


class PlotSqlQuery(PythonTask):
    def __init__(
        self,
        query: str,
        sql_table: SqlTable,
        show_sample_data: bool = False,
        name: str = "plot_sql_query",
        task_id: Optional[str] = None,
        dag_id: Optional[str] = None,
        version: Optional[str] = None,
        enabled: bool = True,
    ):
        super().__init__()
        try:
            self.args: PlotSqlQueryArgs = PlotSqlQueryArgs(
                query=query,
                sql_table=sql_table,
                show_sample_data=show_sample_data,
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


def run_sql_query_pandas(args: PlotSqlQueryArgs) -> bool:

    import pandas as pd
    import matplotlib.pyplot as plt

    query: str = args.query
    sql_table: SqlTable = args.sql_table

    print_info("Running Query:\n{}".format(query))
    df: Optional[pd.DataFrame] = sql_table.run_sql_query(query)

    if df is None:
        print_error("Could not run query")
        return False

    if args.show_sample_data:
        print_info("Sample data:\n{}".format(df.head()))
        print_info("Plotting")
        df.plot("ds", "active_users")
        plt.show(block=False)
        plt.pause(3)
        plt.close()
    return True


def run_sql_query(**kwargs) -> bool:
    args: PlotSqlQueryArgs = PlotSqlQueryArgs(**kwargs)
    return run_sql_query_pandas(args)

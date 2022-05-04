from pathlib import Path
from typing import Optional, Literal, Union, List

from phidata.asset.file import File, FileType
from phidata.asset.table.sql import SqlTable
from phidata.utils.log import logger
from phidata.task import PythonTask, PythonTaskArgs


class UploadFileToSqlArgs(PythonTaskArgs):
    file: File
    sql_table: SqlTable
    # How to behave if the sql_table already exists.
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


class UploadFileToSql(PythonTask):
    def __init__(
        self,
        file: File,
        sql_table: SqlTable,
        if_exists: Optional[Literal["fail", "replace", "append"]] = None,
        index: Optional[bool] = None,
        index_label: Optional[Union[str, List[str]]] = None,
        chunksize: Optional[int] = None,
        name: str = "load_file_to_sql",
        task_id: Optional[str] = None,
        dag_id: Optional[str] = None,
        version: Optional[str] = None,
        enabled: bool = True,
    ):
        super().__init__()
        try:
            self.args: UploadFileToSqlArgs = UploadFileToSqlArgs(
                file=file,
                sql_table=sql_table,
                if_exists=if_exists,
                index=index,
                index_label=index_label,
                chunksize=chunksize,
                name=name,
                task_id=task_id,
                dag_id=dag_id,
                version=version,
                enabled=enabled,
                entrypoint=load_file_to_sql_table,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    @property
    def file(self) -> Optional[File]:
        return self.args.file

    @file.setter
    def file(self, file: File) -> None:
        if file is not None:
            self.args.file = file

    @property
    def sql_table(self) -> Optional[SqlTable]:
        return self.args.sql_table

    @sql_table.setter
    def sql_table(self, sql_table: SqlTable) -> None:
        if sql_table is not None:
            self.args.sql_table = sql_table


def load_file_to_sql_table_pandas(args: UploadFileToSqlArgs) -> bool:

    import pandas as pd

    file_to_load: Optional[File] = args.file
    if file_to_load is None:
        logger.error("File not available")
        return False
    file_path: Optional[Path] = file_to_load.file_path
    if file_path is None:
        logger.error("FilePath not available")
        return False
    file_type: Optional[FileType] = file_to_load.file_type
    if file_type is None:
        logger.error("FileType not available")
        return False
    # logger.debug("File: {}".format(file_to_load.args))

    sql_table: Optional[SqlTable] = args.sql_table
    if sql_table is None:
        logger.error("SqlTable not available")
        return False
    # logger.debug("SqlTable: {}".format(sql_table.args))

    logger.info("Reading: {}".format(file_path))
    df: Optional[pd.DataFrame] = None
    if file_type == FileType.CSV:
        df = pd.read_csv(file_path)
    elif file_type == FileType.JSON:
        df = pd.read_json(file_path)
    elif file_type == FileType.TSV:
        df = pd.read_csv(file_path, sep="\t")

    if df is not None:
        # logger.info()("DataFrame:\n{}".format(df.head()))
        logger.info("Writing to table: {}".format(sql_table.name))
        upload_success = sql_table.write_pandas_df(
            df=df,
            if_exists=args.if_exists,
            index=args.index,
            index_label=args.index_label,
            chunksize=args.chunksize,
        )
        return upload_success
    else:
        logger.info("Could not read file into DataFrame")
        return False


def load_file_to_sql_table(**kwargs) -> bool:
    args: UploadFileToSqlArgs = UploadFileToSqlArgs(**kwargs)
    return load_file_to_sql_table_pandas(args)

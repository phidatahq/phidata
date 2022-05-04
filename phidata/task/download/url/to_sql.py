from pathlib import Path
from typing import Optional, Literal, Union, List

from phidata.asset.file import File, FileType
from phidata.asset.table.sql import SqlTable
from phidata.utils.cli_console import print_info, print_warning
from phidata.utils.log import logger
from phidata.task import PythonTask, PythonTaskArgs


class DownloadUrlToSqlArgs(PythonTaskArgs):
    url: str
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
    # Optional File object to use
    file: Optional[File] = None


class DownloadUrlToSql(PythonTask):
    def __init__(
        self,
        url: str,
        sql_table: SqlTable,
        if_exists: Optional[Literal["fail", "replace", "append"]] = None,
        index: Optional[bool] = None,
        index_label: Optional[Union[str, List[str]]] = None,
        chunksize: Optional[int] = None,
        file: Optional[File] = None,
        name: str = "download_url_to_sql",
        task_id: Optional[str] = None,
        dag_id: Optional[str] = None,
        version: Optional[str] = None,
        enabled: bool = True,
    ):
        super().__init__()
        try:
            self.args: DownloadUrlToSqlArgs = DownloadUrlToSqlArgs(
                url=url,
                sql_table=sql_table,
                if_exists=if_exists,
                index=index,
                index_label=index_label,
                chunksize=chunksize,
                file=file,
                name=name,
                task_id=task_id,
                dag_id=dag_id,
                version=version,
                enabled=enabled,
                entrypoint=download_url_to_sql,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    @property
    def url(self) -> str:
        return self.args.url

    @url.setter
    def url(self, url: str) -> None:
        if url is not None:
            self.args.url = url

    @property
    def sql_table(self) -> Optional[SqlTable]:
        return self.args.sql_table

    @sql_table.setter
    def sql_table(self, sql_table: SqlTable) -> None:
        if sql_table is not None:
            self.args.sql_table = sql_table

    @property
    def file(self) -> Optional[File]:
        return self.args.file

    @file.setter
    def file(self, file: File) -> None:
        if file is not None:
            self.args.file = file


def best_guess_file_name(url: str) -> str:

    from phidata.utils.dttm import get_today_utc_date_str

    fn: Optional[str] = None
    if "/" in url:
        fn = url.split("/")[-1]
    if fn is None:
        fn = f"tmp__{get_today_utc_date_str()}"
    logger.debug("fn: {}".format(fn))
    return fn


def download_url_to_file(args: DownloadUrlToSqlArgs) -> bool:

    import httpx
    import rich.progress

    url = args.url
    if url is None:
        logger.error("URL not available")
        return False

    if args.file is None:
        args.file = File.temporary(best_guess_file_name(args.url))

    file_path: Optional[Path] = args.file.file_path
    if file_path is None:
        logger.error("FilePath not available")
        return False
    file_dir: Path = file_path.parent.resolve()

    # Download URL contents
    print_info("Downloading")
    print_info(f"  Url: {url}")
    print_info(f"  To : {file_path}")

    # Create the directory if it does not exist
    if not file_dir.exists():
        file_dir.mkdir(parents=True, exist_ok=True)

    bytes_to_download: int = 0
    try:
        with file_path.open("w") as open_file:
            with httpx.stream("GET", url) as response:
                try:
                    headers: httpx.Headers = response.headers
                    # logger.debug("headers: {}".format(headers))
                    # logger.debug("status_code: {}".format(response.status_code))
                    bytes_to_download = int(headers["Content-Length"])
                    # logger.debug("bytes_to_download : {}".format(bytes_to_download))
                except Exception:
                    print_warning(f"Could not get total bytes_to_download from headers")

                with rich.progress.Progress(
                    "[progress.percentage]{task.percentage:>3.0f}%",
                    rich.progress.BarColumn(50),
                    rich.progress.DownloadColumn(),
                    rich.progress.TransferSpeedColumn(),
                ) as progress:
                    download_task = progress.add_task(
                        "Download", total=bytes_to_download
                    )
                    for chunk in response.iter_text():
                        open_file.write(chunk)
                        progress.update(
                            download_task, completed=response.num_bytes_downloaded
                        )
        logger.info("Url downloaded")
        return True
    except Exception as e:
        logger.error("Could not download url, please try again")
        logger.exception(e)
    return False


def load_file_to_sql_table_pandas(args: DownloadUrlToSqlArgs) -> bool:

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


def download_url_to_sql(**kwargs) -> bool:

    args: DownloadUrlToSqlArgs = DownloadUrlToSqlArgs.from_kwargs(kwargs)
    # logger.info(f"DownloadUrlToSqlArgs: {args}")

    download_success = download_url_to_file(args)
    if download_success:
        return load_file_to_sql_table_pandas(args)
    return False

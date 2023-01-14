from typing import Optional, Any, List, Dict
from typing_extensions import Literal

from phidata.asset.aws.aws_asset import AwsAsset, AwsAssetArgs
from phidata.checks.check import Check
from phidata.aws.resource.s3.bucket import S3Bucket
from phidata.utils.enums import ExtendedEnum
from phidata.utils.log import logger


class S3TableFormat(ExtendedEnum):
    CSV = "csv"
    IPC = "ipc"
    ARROW = "arrow"
    FEATHER = "feather"
    ORC = "orc"
    PARQUET = "parquet"


class S3TableArgs(AwsAssetArgs):
    # Table Name
    name: str
    # Table Format
    table_format: S3TableFormat
    # Database for the table
    database: str = "default"

    # -*- Table Path
    # S3 Bucket
    bucket: Optional[S3Bucket] = None
    # S3 Bucket Name must be provided if bucket is not provided
    bucket_name: Optional[str] = None
    # Path to table directory in bucket. Without the s3:// prefix
    path: Optional[str] = None
    # To level directory for all tables
    top_level_dir: Optional[str] = None
    # A template string used to generate basenames of written data files.
    # The token ‘{i}’ will be replaced with an automatically incremented integer.
    # If not specified, it defaults to “part-{i}.” + format.default_extname
    basename_template: Optional[str] = None

    # List of partition columns
    partitions: Optional[List[str]] = None

    # Maximum number of partitions any batch may be written into.
    max_partitions: Optional[int] = None
    # If greater than 0 then this will limit the maximum number of files that can be left open.
    # If an attempt is made to open too many files then the least recently used file will be closed.
    # If this setting is set too low you may end up fragmenting your data into many small files.
    max_open_files: Optional[int] = None
    # Maximum number of rows per file. If greater than 0 then this will limit how many rows are placed in any single
    # file. Otherwise there will be no limit and one file will be created in each output directory unless files need
    # to be closed to respect max_open_files
    max_rows_per_file: Optional[int] = None
    # Minimum number of rows per group. When the value is greater than 0, the dataset writer will batch incoming data
    # and only write the row groups to the disk when sufficient rows have accumulated.
    min_rows_per_group: Optional[int] = None
    # Maximum number of rows per group. If the value is greater than 0, then the dataset writer may split up large
    # incoming batches into multiple row groups. If this value is set, then min_rows_per_group should also be set.
    # Otherwise it could end up with very small row groups.
    max_rows_per_group: Optional[int] = None
    # Controls how the dataset will handle data that already exists in the destination.
    # The default behavior (‘error’) is to raise an error if any data exists in the destination.
    # ‘overwrite_or_ignore’ will ignore any existing data and will overwrite files with the same name
    # as an output file. Other existing files will be ignored. This behavior, in combination with a unique
    # basename_template for each write, will allow for an append workflow.
    # ‘delete_matching’ is useful when you are writing a partitioned dataset.
    # The first time each partition directory is encountered the entire directory will be deleted.
    # This allows you to overwrite old partitions completely.
    write_mode: Literal[
        "delete_matching", "overwrite_or_ignore", "error"
    ] = "delete_matching"


class S3Table(AwsAsset):
    """Base Class for S3 tables"""

    def __init__(
        self,
        # Table Name: required
        name: str,
        # Table Format: required
        table_format: S3TableFormat,
        # Database for the table
        database: str = "default",
        # DataModel for this table
        data_model: Optional[Any] = None,
        # Checks to run before reading from disk
        read_checks: Optional[List[Check]] = None,
        # Checks to run before writing to disk
        write_checks: Optional[List[Check]] = None,
        # -*- Table Path
        # S3 Bucket
        bucket: Optional[S3Bucket] = None,
        # S3 Bucket Name
        bucket_name: Optional[str] = None,
        # Path to table directory in bucket. Without the s3:// prefix
        path: Optional[str] = None,
        # To level directory for all tables
        top_level_dir: Optional[str] = "tables",
        # A template string used to generate basenames of written data files.
        # The token ‘{i}’ will be replaced with an automatically incremented integer.
        # If not specified, it defaults to “part-{i}.” + format.default_extname
        basename_template: Optional[str] = None,
        # List of partition columns
        partitions: Optional[List[str]] = None,
        # Maximum number of partitions any batch may be written into.
        max_partitions: Optional[int] = None,
        # If greater than 0 then this will limit the maximum number of files that can be left open.
        # If an attempt is made to open too many files then the least recently used file will be closed.
        # If this setting is set too low you may end up fragmenting your data into many small files.
        max_open_files: Optional[int] = None,
        # Maximum number of rows per file. If greater than 0 then this will limit how many rows are placed in any single
        # file. Otherwise there will be no limit and one file will be created in each output directory unless files need
        # to be closed to respect max_open_files
        max_rows_per_file: Optional[int] = None,
        # Minimum number of rows per group. When the value is greater than 0, the dataset writer will batch incoming data
        # and only write the row groups to the disk when sufficient rows have accumulated.
        min_rows_per_group: Optional[int] = None,
        # Maximum number of rows per group. If the value is greater than 0, then the dataset writer may split up large
        # incoming batches into multiple row groups. If this value is set, then min_rows_per_group should also be set.
        # Otherwise it could end up with very small row groups.
        max_rows_per_group: Optional[int] = None,
        # Controls how the dataset will handle data that already exists in the destination.
        # The default behavior (‘error’) is to raise an error if any data exists in the destination.
        # ‘overwrite_or_ignore’ will ignore any existing data and will overwrite files with the same name
        # as an output file. Other existing files will be ignored. This behavior, in combination with a unique
        # basename_template for each write, will allow for an append workflow.
        # ‘delete_matching’ is useful when you are writing a partitioned dataset.
        # The first time each partition directory is encountered the entire directory will be deleted.
        # This allows you to overwrite old partitions completely.
        write_mode: Literal[
            "delete_matching", "overwrite_or_ignore", "error"
        ] = "delete_matching",
        version: Optional[str] = None,
        enabled: bool = True,
        **kwargs,
    ) -> None:
        super().__init__()
        try:
            self.args: S3TableArgs = S3TableArgs(
                name=name,
                table_format=table_format,
                database=database,
                data_model=data_model,
                read_checks=read_checks,
                write_checks=write_checks,
                bucket=bucket,
                bucket_name=bucket_name,
                path=path,
                top_level_dir=top_level_dir,
                basename_template=basename_template,
                partitions=partitions,
                max_partitions=max_partitions,
                max_open_files=max_open_files,
                max_rows_per_file=max_rows_per_file,
                min_rows_per_group=min_rows_per_group,
                max_rows_per_group=max_rows_per_group,
                write_mode=write_mode,
                version=version,
                enabled=enabled,
                **kwargs,
            )
        except Exception as e:
            logger.error(f"Args for {self.name} are not valid")
            raise

    @property
    def table_format(self) -> Optional[S3TableFormat]:
        return self.args.table_format if self.args else None

    @table_format.setter
    def table_format(self, table_format: S3TableFormat) -> None:
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
    def bucket(self) -> Optional[S3Bucket]:
        return self.args.bucket if self.args else None

    @bucket.setter
    def bucket(self, bucket: S3Bucket) -> None:
        if self.args and bucket:
            self.args.bucket = bucket

    @property
    def bucket_name(self) -> Optional[str]:
        return self.args.bucket_name if self.args else None

    @bucket_name.setter
    def bucket_name(self, bucket_name: str) -> None:
        if self.args and bucket_name:
            self.args.bucket_name = bucket_name

    @property
    def path(self) -> Optional[str]:
        return self.args.path if self.args else None

    @path.setter
    def path(self, path: str) -> None:
        if self.args and path:
            self.args.path = path

    @property
    def top_level_dir(self) -> Optional[str]:
        return self.args.top_level_dir if self.args else None

    @top_level_dir.setter
    def top_level_dir(self, top_level_dir: str) -> None:
        if self.args and top_level_dir:
            self.args.top_level_dir = top_level_dir

    @property
    def basename_template(self) -> Optional[str]:
        return self.args.basename_template if self.args else None

    @basename_template.setter
    def basename_template(self, basename_template: str) -> None:
        if self.args and basename_template:
            self.args.basename_template = basename_template

    @property
    def partitions(self) -> Optional[List[str]]:
        return self.args.partitions if self.args else None

    @partitions.setter
    def partitions(self, partitions: List[str]) -> None:
        if self.args and partitions:
            self.args.partitions = partitions

    @property
    def max_partitions(self) -> Optional[int]:
        return self.args.max_partitions if self.args else None

    @max_partitions.setter
    def max_partitions(self, max_partitions: int) -> None:
        if self.args and max_partitions:
            self.args.max_partitions = max_partitions

    @property
    def max_open_files(self) -> Optional[int]:
        return self.args.max_open_files if self.args else None

    @max_open_files.setter
    def max_open_files(self, max_open_files: int) -> None:
        if self.args and max_open_files:
            self.args.max_open_files = max_open_files

    @property
    def max_rows_per_file(self) -> Optional[int]:
        return self.args.max_rows_per_file if self.args else None

    @max_rows_per_file.setter
    def max_rows_per_file(self, max_rows_per_file: int) -> None:
        if self.args and max_rows_per_file:
            self.args.max_rows_per_file = max_rows_per_file

    @property
    def min_rows_per_group(self) -> Optional[int]:
        return self.args.min_rows_per_group if self.args else None

    @min_rows_per_group.setter
    def min_rows_per_group(self, min_rows_per_group: int) -> None:
        if self.args and min_rows_per_group:
            self.args.min_rows_per_group = min_rows_per_group

    @property
    def max_rows_per_group(self) -> Optional[int]:
        return self.args.max_rows_per_group if self.args else None

    @max_rows_per_group.setter
    def max_rows_per_group(self, max_rows_per_group: int) -> None:
        if self.args and max_rows_per_group:
            self.args.max_rows_per_group = max_rows_per_group

    @property
    def write_mode(
        self,
    ) -> Optional[Literal["delete_matching", "overwrite_or_ignore", "error"]]:
        return self.args.write_mode if self.args else None

    @write_mode.setter
    def write_mode(
        self, write_mode: Literal["delete_matching", "overwrite_or_ignore", "error"]
    ) -> None:
        if self.args and write_mode:
            self.args.write_mode = write_mode

    @property
    def table_location(self) -> str:
        if self.path is not None:
            return self.path
        else:
            if self.bucket_name is not None:
                return "{}/{}{}/{}".format(
                    self.bucket_name,
                    f"{self.top_level_dir}/" if self.top_level_dir else "",
                    self.database,
                    self.name,
                )
            if self.bucket is not None:
                return "{}/{}{}/{}".format(
                    self.bucket.name,
                    f"{self.top_level_dir}/" if self.top_level_dir else "",
                    self.database,
                    self.name,
                )
        return ""

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

    def write_table(self, table: Any, **write_options) -> bool:
        """
        Write pyarrow.Table to disk.

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

        # Validate table
        if table is None or not isinstance(table, pa.Table):
            logger.error("Table invalid")
            return False

        # Check table_location is available
        table_location = self.table_location
        if table_location is None:
            logger.error("Table location invalid")
            return False

        # Check S3FileSystem is available
        fs = self._get_fs()
        if fs is None:
            logger.error("Could not create S3FileSystem")
            return False

        logger.debug("Format: {}".format(self.args.table_format.value))
        try:
            # Run write checks
            if self.write_checks is not None:
                for check in self.write_checks:
                    if not check.check_table(table):
                        return False

            # Create a dict of args which are not null
            not_null_args: Dict[str, Any] = {}
            if self.args.basename_template is not None:
                not_null_args["basename_template"] = self.args.basename_template
            if self.args.partitions is not None:
                not_null_args["partitioning"] = self.args.partitions
                not_null_args["partitioning_flavor"] = "hive"
                # cast partition keys to string
                # ref: https://bneijt.nl/blog/write-polars-dataframe-as-parquet-dataset/
                table = table.cast(
                    pa.schema(
                        [
                            f.with_type(pa.string())
                            if f.name in self.args.partitions
                            else f
                            for f in table.schema
                        ]
                    )
                )
            if self.args.max_partitions is not None:
                not_null_args["max_partitions"] = self.args.max_partitions
            if self.args.max_open_files is not None:
                not_null_args["max_open_files"] = self.args.max_open_files
            if self.args.max_rows_per_file is not None:
                not_null_args["max_rows_per_file"] = self.args.max_rows_per_file
            if self.args.min_rows_per_group is not None:
                not_null_args["min_rows_per_group"] = self.args.min_rows_per_group
            if self.args.max_rows_per_group is not None:
                not_null_args["max_rows_per_group"] = self.args.max_rows_per_group

            # Build file_options: FileFormat specific write options
            # created using the FileFormat.make_write_options() function.
            if write_options:
                file_options = ds.FileFormat.make_write_options(**write_options)
                not_null_args["file_options"] = file_options

            # Write table to disk
            ds.write_dataset(
                table,
                table_location,
                format=self.args.table_format.value,
                filesystem=fs,
                existing_data_behavior=self.args.write_mode,
                **not_null_args,
            )
            logger.info(f"Table {self.name} written to {table_location}")

            return True
        except Exception:
            logger.error("Could not write table: {}".format(self.name))
            raise

    def write_polars_df(
        self,
        df: Optional[Any] = None,
        options: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> bool:
        """
        Write Polars DataFrame to disk.
        """
        # Validate polars is installed
        try:
            import polars as pl  # type: ignore
        except ImportError as ie:
            logger.error(f"Polars not installed: {ie}")
            return False

        # Validate df
        if df is None or not isinstance(df, pl.DataFrame):
            logger.error("DataFrame invalid")
            return False

        # Create arrow table and write to disk
        return self.write_table(df.to_arrow(), options=options)

    def write_pandas_df(self, df: Optional[Any] = None, **kwargs) -> bool:
        logger.debug(f"@write_pandas_df not defined for {self.name}")
        return False

    ######################################################
    ## Create DataAsset
    ######################################################

    def _create(self) -> bool:
        logger.error(f"@_create not defined for {self.name}")
        return False

    def post_create(self) -> bool:
        return True

    ######################################################
    ## Read DataAsset
    ######################################################

    def read_table(self, **read_options) -> Optional[Any]:
        """
        Read pyarrow.Table from disk.

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

        # Check table_location is available
        table_location = self.table_location
        if table_location is None:
            logger.error("Table location invalid")
            return False

        # Check S3FileSystem is available
        fs = self._get_fs()
        if fs is None:
            logger.error("Could not create S3FileSystem")
            return False

        logger.debug("Format: {}".format(self.args.table_format.value))
        try:
            # Create a dict of args which are not null
            not_null_args: Dict[str, Any] = {}
            if self.args.partitions is not None:
                not_null_args["partitioning"] = "hive"

            # Read dataset from s3
            # https://arrow.apache.org/docs/python/generated/pyarrow.dataset.dataset.html#pyarrow.dataset.dataset
            # https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Dataset.html#pyarrow.dataset.Dataset
            dataset: ds.Dataset = ds.dataset(
                table_location,
                format=self.args.table_format.value,
                filesystem=fs,
                **not_null_args,
            )

            # Convert dataset to table
            # https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Dataset.html#pyarrow.dataset.Dataset.to_table
            table: pa.Table = dataset.to_table(**read_options)

            # Run read checks
            if self.read_checks is not None:
                for check in self.read_checks:
                    if not check.check_table(table):
                        return None

            return table
        except Exception:
            logger.error("Could not read table: {}".format(self.name))
            raise

    def read_polars_df(
        self, options: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Optional[Any]:
        """
        Read Polars DataFrame from disk.

        options: Dict[str, Any]
            Additional options to pass to the reader.
            More info:
                https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Scanner.html#pyarrow.dataset.Scanner.from_dataset
                https://arrow.apache.org/docs/python/generated/pyarrow.dataset.dataset.html#pyarrow.dataset.dataset.to_table
        """
        # Validate polars is installed
        try:
            import polars as pl
        except ImportError as ie:
            logger.error(f"Polars not installed: {ie}")
            return None

        # Convert table to polars DataFrame
        # https://pola-rs.github.io/polars/py-polars/html/reference/api/polars.from_arrow.html
        return pl.from_arrow(self.read_table(options=options))

    def read_pandas_df(self, **kwargs) -> Optional[Any]:
        logger.debug(f"@read_pandas_df not defined for {self.name}")
        return False

    def _read(self) -> Any:
        logger.error(f"@_read not defined for {self.name}")
        return False

    ######################################################
    ## Update DataAsset
    ######################################################

    def _update(self) -> Any:
        logger.error(f"@_update not defined for {self.name}")
        return False

    def post_update(self) -> bool:
        return True

    ######################################################
    ## Delete DataAsset
    ######################################################

    def _delete(self) -> Any:
        logger.error(f"@_delete not defined for {self.name}")
        return False

    def post_delete(self) -> bool:
        return True

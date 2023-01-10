from typing import Optional, Any, Union, List, Dict
from typing_extensions import Literal

from phidata.asset.aws.aws_asset import AwsAsset, AwsAssetArgs
from phidata.infra.aws.resource.s3.bucket import S3Bucket
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
    # Database for the table
    db_name: str = "default"
    # DataModel for this table
    data_model: Optional[Any] = None
    # S3 Table Format
    table_format: S3TableFormat

    # S3 Bucket
    bucket: Optional[S3Bucket] = None
    # S3 Bucket Name must be provided if bucket is not provided
    bucket_name: Optional[str] = None
    # S3 Full Path URI
    path: Optional[str] = None
    # To level directory for all tables
    top_level_dir: Optional[str] = "tables"
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
    """Base Class for Sql tables"""

    def __init__(
        self,
        # Table Name: required
        name: str,
        # S3 Table Format: required
        table_format: S3TableFormat,
        # Database for the table
        db_name: str = "default",
        # DataModel for this table
        data_model: Optional[Any] = None,
        # S3 Bucket
        bucket: Optional[S3Bucket] = None,
        # S3 Bucket Name
        bucket_name: Optional[str] = None,
        # S3 Full Path URI
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
        self.args: Optional[S3TableArgs] = None
        if name is None:
            raise ValueError("name is required")
        if table_format is None:
            raise ValueError("table_format is required")

        try:
            self.args = S3TableArgs(
                name=name,
                table_format=table_format,
                db_name=db_name,
                data_model=data_model,
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
    def table_location(self) -> str:
        if self.args is None:
            raise ValueError("args not set")

        if self.args.path is not None:
            return self.args.path
        else:
            if self.args.bucket_name is not None:
                return "{}/{}{}/{}".format(
                    self.args.bucket_name,
                    f"{self.args.top_level_dir}/" if self.args.top_level_dir else "",
                    self.args.db_name,
                    self.args.name,
                )
            if self.args.bucket is not None:
                return "{}/{}{}/{}".format(
                    self.args.bucket.name,
                    f"{self.args.top_level_dir}/" if self.args.top_level_dir else "",
                    self.args.db_name,
                    self.args.name,
                )
        return ""

    ######################################################
    ## Get FileSystem
    ######################################################

    def _get_fs(self) -> Optional[Any]:
        from pyarrow import fs

        logger.debug("initializing S3FileSystem")
        if self.aws_region is not None:
            return fs.S3FileSystem(region=self.aws_region)
        else:
            return fs.S3FileSystem()

    ######################################################
    ## Build data asset
    ######################################################

    def build(self) -> bool:
        logger.debug(f"@build not defined for {self.name}")
        return False

    ######################################################
    ## Create DataAsset
    ######################################################

    def is_valid(self) -> bool:
        return True

    def _create(self) -> bool:
        logger.error(f"@_create not defined for {self.name}")
        return False

    def post_create(self) -> bool:
        return True

    def write_df(self, df: Optional[Any] = None, **write_options) -> bool:
        """
        Write DataFrame to table.
        """

        # S3Table not yet initialized
        if self.args is None:
            return False

        # Check name is available
        if self.name is None:
            logger.error("Table name invalid")
            return False

        # Validate polars is installed
        try:
            import polars as pl
        except ImportError as ie:
            logger.error(f"Polars not installed: {ie}")
            return False

        # Validate pyarrow is installed
        try:
            import pyarrow
            import pyarrow.dataset
        except ImportError as ie:
            logger.error(f"PyArrow not installed: {ie}")
            return False

        # Validate df
        if df is None or not isinstance(df, pl.DataFrame):
            logger.error("DataFrame invalid")
            return False

        try:
            logger.debug("Format: {}".format(self.args.table_format.value))

            # Create arrow table
            arrow_table = df.to_arrow()
            if arrow_table is None:
                logger.error("Could not create Arrow table")
                return False
            # logger.debug(f"arrow_table: {type(arrow_table)}")
            # logger.debug(f"arrow_table: {arrow_table}")

            # S3 path for the table
            table_location = self.table_location
            if table_location is None:
                logger.error("Table location invalid")
                return False
            # logger.debug(f"table_location: {type(table_location)}")
            # logger.debug(f"table_location: {table_location}")

            # Create S3FileSystem
            fs = self._get_fs()
            if fs is None:
                logger.error("Could not create S3FileSystem")
                return False
            # logger.debug(f"fs: {type(fs)}")
            # logger.debug(f"fs: {fs}")

            # Create a dict of args which are not null
            not_null_args: Dict[str, Any] = {}
            if self.args.basename_template is not None:
                not_null_args["basename_template"] = self.args.basename_template
            if self.args.partitions is not None:
                not_null_args["partitioning"] = self.args.partitions
                not_null_args["partitioning_flavor"] = "hive"
                # cast partition keys to string
                # ref: https://bneijt.nl/blog/write-polars-dataframe-as-parquet-dataset/
                arrow_table = arrow_table.cast(
                    pyarrow.schema(
                        [
                            f.with_type(pyarrow.string())
                            if f.name in self.args.partitions
                            else f
                            for f in arrow_table.schema
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
                file_options = pyarrow.dataset.FileFormat.make_write_options(
                    **write_options
                )
                not_null_args["file_options"] = file_options

            # Write table to s3
            pyarrow.dataset.write_dataset(
                arrow_table,
                table_location,
                format=self.args.table_format.value,
                filesystem=fs,
                existing_data_behavior=self.args.write_mode,
                **not_null_args,
            )
            return True
        except Exception:
            logger.error("Could not write table: {}".format(self.name))
            raise

    def write_pandas_df(self, df: Optional[Any] = None) -> bool:
        logger.debug(f"@write_pandas_df not defined for {self.name}")
        return False

    ######################################################
    ## Read DataAsset
    ######################################################

    def read_df(self) -> Optional[Any]:
        logger.debug(f"@read_df not defined for {self.name}")
        return False

    def read_pandas_df(self) -> Optional[Any]:
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

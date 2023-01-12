from typing import Optional, Any, List
from typing_extensions import Literal

from phidata.table.s3.s3_table import S3Table, S3TableArgs, S3TableFormat
from phidata.checks.check import Check
from phidata.aws.resource.s3.bucket import S3Bucket


class CsvTableS3(S3Table):
    def __init__(
        self,
        # Table Name: required
        name: str,
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
        # S3 Full Path URI
        path: Optional[str] = None,
        # -*- Build S3 Path using
        top_level_dir: Optional[str] = "tables",
        path_prefix: Optional[str] = None,
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
        super().__init__(
            name=name,
            table_format=S3TableFormat.CSV,
            database=database,
            data_model=data_model,
            read_checks=read_checks,
            write_checks=write_checks,
            bucket=bucket,
            bucket_name=bucket_name,
            path=path,
            top_level_dir=top_level_dir,
            path_prefix=path_prefix,
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

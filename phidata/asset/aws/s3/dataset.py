from typing import Optional, Literal, List, Tuple, Dict, Any, Union

from phidata.asset.aws import AwsAsset, AwsAssetArgs
from phidata.infra.aws.resource.s3.bucket import S3Bucket
from phidata.utils.enums import ExtendedEnum
from phidata.utils.log import logger


class S3DatasetType(ExtendedEnum):
    CSV = "CSV"
    JSON = "JSON"
    PARQUET = "PARQUET"


class S3DatasetArgs(AwsAssetArgs):
    # Dataset name, used as the table name
    name: str
    # Type of dataset: CSV, JSON, PARQUET
    dataset_type: S3DatasetType
    # Glue/Athena catalog: Table name.
    table: Optional[str] = None
    # Glue/Athena catalog: Database name.
    database: Optional[str] = None
    # The type of the Glue Table. Set to EXTERNAL_TABLE if None.
    table_type: Optional[str] = None
    # Glue/Athena catalog: Table description
    table_description: Optional[str] = None
    # write mode – append (Default), overwrite, overwrite_partitions.
    write_mode: Optional[Literal["append", "overwrite", "overwrite_partitions"]] = None

    # S3 path for the dataset. If not provided, inferred from
    # path_prefix/top_level_dir/database/table or
    # s3://bucket/top_level_dir/database/table
    path: Optional[str] = None
    # Top level directory for all s3 datasets.
    top_level_dir: Optional[str] = "datasets"
    # Prefix for the dataset path. Used to infer dataset path if not provided as
    # path_prefix/top_level_dir/database/table
    path_prefix: Optional[str] = None
    # S3 bucket for the dataset. Used to infer dataset path if not provided as
    # s3://bucket/top_level_dir/database/table
    bucket: Optional[S3Bucket] = None
    # If dataset=True, add a filename prefix to the output files.
    filename_prefix: Optional[str] = None

    # Dictionary of columns names and Athena/Glue types to be casted.
    # Useful when you have columns with undetermined or mixed data types.
    # (e.g. {‘col name’: ‘bigint’, ‘col2 name’: ‘int’})
    dtype: Optional[Dict[str, str]] = None
    # Glue/Athena catalog: Key/value pairs to tag the table.
    parameters: Optional[Dict[str, str]] = None
    # Glue/Athena catalog: Columns names and the related comments
    # (e.g. {‘col0’: ‘Column 0.’, ‘col1’: ‘Column 1.’, ‘col2’: ‘Partition.’}).
    columns_comments: Optional[Dict[str, str]] = None

    # List of column names that will be used to create partitions.
    partition_cols: Optional[List[str]] = None
    # Tuple consisting of the column names used for
    # bucketing as the first element and the number of buckets as the second element.
    # Only str, int and bool are supported as column data types for bucketing.
    bucketing_info: Optional[Tuple[List[str], int]] = None
    # If True will increase the parallelism level during the partitions writing.
    # It will decrease the writing time and increase the memory usage.
    # https://aws-sdk-pandas.readthedocs.io/en/2.17.0/tutorials/022%20-%20Writing%20Partitions%20Concurrently.html
    concurrent_partitioning: Optional[bool] = None

    # If True and mode=”overwrite”, creates an archived version of the table catalog before updating it.
    catalog_versioning: Optional[bool] = None
    # If True allows schema evolution (new or missing columns), otherwise a exception will be raised.
    # True by default. (Only considered if mode in (“append”, “overwrite_partitions”))
    schema_evolution: Optional[bool] = None
    # The ID of the Data Catalog from which to retrieve Databases.
    # If none is provided, the AWS account ID is used by default.
    catalog_id: Optional[str] = None

    # True to enable concurrent requests, False to disable multiple threads.
    # If enabled os.cpu_count() will be used as the max number of threads.
    # If integer is provided, specified number is used.
    use_threads: Optional[Union[bool, int]] = None
    # Boto3 Session. The default boto3 Session will be used if boto3_session receive None.
    boto3_session: Optional[Any] = None
    # Forwarded to botocore requests.
    # e.g. s3_additional_kwargs={‘ServerSideEncryption’: ‘aws:kms’, ‘SSEKMSKeyId’: ‘YOUR_KMS_KEY_ARN’}
    s3_additional_kwargs: Optional[Dict[str, Any]] = None

    # regular_partitions (bool) – Create regular partitions (Non projected partitions) on Glue Catalog.
    # Disable when you will work only with Partition Projection.
    regular_partitions: Optional[bool] = None
    # Enable Partition Projection on Athena
    # https://docs.aws.amazon.com/athena/latest/ug/partition-projection.html
    projection_enabled: Optional[bool] = None
    # Dictionary of partitions names and Athena projections types. Valid types: “enum”, “integer”, “date”, “injected”
    # https://docs.aws.amazon.com/athena/latest/ug/partition-projection-supported-types.html
    # e.g. {‘col_name’: ‘enum’, ‘col2_name’: ‘integer’}
    projection_types: Optional[Dict[str, str]] = None
    # Dictionary of partitions names and Athena projections ranges.
    # https://docs.aws.amazon.com/athena/latest/ug/partition-projection-supported-types.html
    # e.g. {‘col_name’: ‘0,10’, ‘col2_name’: ‘-1,8675309’}
    projection_ranges: Optional[Dict[str, str]] = None
    # Dictionary of partitions names and Athena projections values.
    # https://docs.aws.amazon.com/athena/latest/ug/partition-projection-supported-types.html
    # e.g. {‘col_name’: ‘A,B,Unknown’, ‘col2_name’: ‘foo,boo,bar’}
    projection_values: Optional[Dict[str, str]] = None
    # Dictionary of partitions names and Athena projections intervals.
    # https://docs.aws.amazon.com/athena/latest/ug/partition-projection-supported-types.html
    # e.g. {‘col_name’: ‘1’, ‘col2_name’: ‘5’}
    projection_intervals: Optional[Dict[str, str]] = None
    # Dictionary of partitions names and Athena projections digits.
    # https://docs.aws.amazon.com/athena/latest/ug/partition-projection-supported-types.html
    # e.g. {‘col_name’: ‘1’, ‘col2_name’: ‘2’}
    projection_digits: Optional[Dict[str, str]] = None
    # Dictionary of partitions names and Athena projections formats.
    # https://docs.aws.amazon.com/athena/latest/ug/partition-projection-supported-types.html
    # e.g. {‘col_date’: ‘yyyy-MM-dd’, ‘col2_timestamp’: ‘yyyy-MM-dd HH:mm:ss’}
    projection_formats: Optional[Dict[str, str]] = None
    # Value which is allows Athena to properly map partition values if the S3 file locations
    # do not follow a typical …/column=value/… pattern.
    # https://docs.aws.amazon.com/athena/latest/ug/partition-projection-setting-up.html
    # e.g. s3://bucket/table_root/a=${a}/${b}/some_static_subdirectory/${c}/
    projection_storage_location_template: Optional[str] = None


class S3Dataset(AwsAsset):
    def __init__(
        self,
        name: Optional[str] = None,
        dataset_type: Optional[S3DatasetType] = None,
        table: Optional[str] = None,
        database: Optional[str] = None,
        table_type: Optional[str] = None,
        table_description: Optional[str] = None,
        write_mode: Optional[
            Literal["append", "overwrite", "overwrite_partitions"]
        ] = None,
        path: Optional[str] = None,
        top_level_dir: Optional[str] = "datasets",
        path_prefix: Optional[str] = None,
        bucket: Optional[S3Bucket] = None,
        filename_prefix: Optional[str] = None,
        dtype: Optional[Dict[str, str]] = None,
        parameters: Optional[Dict[str, str]] = None,
        columns_comments: Optional[Dict[str, str]] = None,
        partition_cols: Optional[List[str]] = None,
        bucketing_info: Optional[Tuple[List[str], int]] = None,
        concurrent_partitioning: Optional[bool] = None,
        catalog_versioning: Optional[bool] = None,
        schema_evolution: Optional[bool] = None,
        catalog_id: Optional[str] = None,
        use_threads: Optional[Union[bool, int]] = None,
        boto3_session: Optional[Any] = None,
        s3_additional_kwargs: Optional[Dict[str, Any]] = None,
        regular_partitions: Optional[bool] = None,
        projection_enabled: Optional[bool] = None,
        projection_types: Optional[Dict[str, str]] = None,
        projection_ranges: Optional[Dict[str, str]] = None,
        projection_values: Optional[Dict[str, str]] = None,
        projection_intervals: Optional[Dict[str, str]] = None,
        projection_digits: Optional[Dict[str, str]] = None,
        projection_formats: Optional[Dict[str, str]] = None,
        projection_storage_location_template: Optional[str] = None,
        version: Optional[str] = None,
        enabled: bool = True,
    ) -> None:

        super().__init__()
        try:
            self.args: S3DatasetArgs = S3DatasetArgs(
                name=name,
                dataset_type=dataset_type,
                table=table,
                database=database,
                table_type=table_type,
                table_description=table_description,
                write_mode=write_mode,
                path=path,
                top_level_dir=top_level_dir,
                path_prefix=path_prefix,
                bucket=bucket,
                filename_prefix=filename_prefix,
                dtype=dtype,
                parameters=parameters,
                columns_comments=columns_comments,
                partition_cols=partition_cols,
                bucketing_info=bucketing_info,
                concurrent_partitioning=concurrent_partitioning,
                catalog_versioning=catalog_versioning,
                schema_evolution=schema_evolution,
                catalog_id=catalog_id,
                use_threads=use_threads,
                boto3_session=boto3_session,
                s3_additional_kwargs=s3_additional_kwargs,
                regular_partitions=regular_partitions,
                projection_enabled=projection_enabled,
                projection_types=projection_types,
                projection_ranges=projection_ranges,
                projection_values=projection_values,
                projection_intervals=projection_intervals,
                projection_digits=projection_digits,
                projection_formats=projection_formats,
                projection_storage_location_template=projection_storage_location_template,
                version=version,
                enabled=enabled,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    @property
    def dataset_type(self) -> Optional[S3DatasetType]:
        return self.args.dataset_type

    @dataset_type.setter
    def dataset_type(self, dataset_type: S3DatasetType) -> None:
        if dataset_type is not None:
            self.args.dataset_type = dataset_type

    @property
    def table(self) -> Optional[str]:
        return self.args.table

    @table.setter
    def table(self, table: str) -> None:
        if table is not None:
            self.args.table = table

    @property
    def database(self) -> Optional[str]:
        return self.args.database

    @database.setter
    def database(self, database: str) -> None:
        if database is not None:
            self.args.database = database

    @property
    def table_type(self) -> Optional[str]:
        return self.args.table_type

    @table_type.setter
    def table_type(self, table_type: str) -> None:
        if table_type is not None:
            self.args.table_type = table_type

    @property
    def table_description(self) -> Optional[str]:
        return self.args.table_description

    @table_description.setter
    def table_description(self, table_description: str) -> None:
        if table_description is not None:
            self.args.table_description = table_description

    @property
    def write_mode(
        self,
    ) -> Optional[Literal["append", "overwrite", "overwrite_partitions"]]:
        return self.args.write_mode

    @write_mode.setter
    def write_mode(
        self, write_mode: Literal["append", "overwrite", "overwrite_partitions"]
    ) -> None:
        if write_mode is not None:
            self.args.write_mode = write_mode

    @property
    def path(self) -> Optional[str]:
        return self.args.path

    @path.setter
    def path(self, path: str) -> None:
        if path is not None:
            self.args.path = path

    @property
    def top_level_dir(self) -> Optional[str]:
        return self.args.top_level_dir

    @top_level_dir.setter
    def top_level_dir(self, top_level_dir: str) -> None:
        if top_level_dir is not None:
            self.args.top_level_dir = top_level_dir

    @property
    def path_prefix(self) -> Optional[str]:
        return self.args.path_prefix

    @path_prefix.setter
    def path_prefix(self, path_prefix: str) -> None:
        if path_prefix is not None:
            self.args.path_prefix = path_prefix

    @property
    def bucket(self) -> Optional[S3Bucket]:
        return self.args.bucket

    @bucket.setter
    def bucket(self, bucket: S3Bucket) -> None:
        if bucket is not None:
            self.args.bucket = bucket

    @property
    def filename_prefix(self) -> Optional[str]:
        return self.args.filename_prefix

    @filename_prefix.setter
    def filename_prefix(self, filename_prefix: str) -> None:
        if filename_prefix is not None:
            self.args.filename_prefix = filename_prefix

    @property
    def uri(self) -> str:
        if self.path is not None:
            return self.path
        else:
            if self.path_prefix is not None:
                return "{}/{}{}/{}".format(
                    self.path_prefix,
                    f"{self.top_level_dir}/" if self.top_level_dir else "",
                    self.database,
                    self.table,
                )
            if self.bucket is not None:
                return "{}/{}{}/{}".format(
                    self.bucket.get_uri(),
                    f"{self.top_level_dir}/" if self.top_level_dir else "",
                    self.database,
                    self.table,
                )
        return ""

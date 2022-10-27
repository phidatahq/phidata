from typing import Optional, Literal, List, Tuple, Dict, Any, Union

from phidata.asset.aws.s3.dataset_base import (
    S3DatasetBase,
    S3DatasetBaseArgs,
    S3DatasetType,
)
from phidata.task import Task
from phidata.check import Check
from phidata.infra.aws.resource.s3.bucket import S3Bucket
from phidata.utils.log import logger


class S3DatasetCsvArgs(S3DatasetBaseArgs):
    sep: str = ","


class S3DatasetCsv(S3DatasetBase):
    def __init__(
        self,
        table: str,
        sep: str = ",",
        database: str = "default",
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
        **kwargs,
    ) -> None:

        super().__init__()
        try:
            self.args: S3DatasetCsvArgs = S3DatasetCsvArgs(
                name=f"{database}.{table}",
                sep=sep,
                dataset_type=S3DatasetType.CSV,
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
                **kwargs,
            )
        except Exception as e:
            logger.error(f"Args for {self.name} are not valid")
            raise

    @property
    def sep(self) -> Optional[str]:
        return self.args.sep

    @sep.setter
    def sep(self, sep: str) -> None:
        if sep is not None:
            self.args.sep = sep

    ######################################################
    ## Write dataset
    ######################################################

    def write_pandas_df(
        self,
        df: Optional[Any] = None,
        # S3 path for the dataset or use the path defined in the dataset
        path: Optional[str] = None,
        # String of length 1. Field delimiter for the output file.
        sep: Optional[str] = None,
        # Write row names (index)
        index: Optional[bool] = None,
        # Columns to write.
        columns: Optional[List[str]] = None,
        # True to enable concurrent requests, False to disable multiple threads.,
        # If enabled os.cpu_count() will be used as the max number of threads.,
        # If integer is provided, specified number is used.,
        use_threads: Optional[Union[bool, int]] = None,
        # Boto3 Session. The default boto3 Session will be used if boto3_session receive None.,
        boto3_session: Optional[Any] = None,
        # Forwarded to botocore requests.,
        # e.g. s3_additional_kwargs={‘ServerSideEncryption’: ‘aws:kms’, ‘SSEKMSKeyId’: ‘YOUR_KMS_KEY_ARN’},
        s3_additional_kwargs: Optional[Dict[str, Any]] = None,
        # Add a filename prefix to the output files.
        filename_prefix: Optional[str] = None,
        # List of column names that will be used to create partitions.,
        partition_cols: Optional[List[str]] = None,
        # Tuple consisting of the column names used for,
        # bucketing as the first element and the number of buckets as the second element.,
        # Only str, int and bool are supported as column data types for bucketing.,
        bucketing_info: Optional[Tuple[List[str], int]] = None,
        # If True will increase the parallelism level during the partitions writing.,
        # It will decrease the writing time and increase the memory usage.,
        # https://aws-sdk-pandas.readthedocs.io/en/2.17.0/tutorials/022%20-%20Writing%20Partitions%20Concurrently.html,
        concurrent_partitioning: Optional[bool] = None,
        # write mode – append (Default), overwrite, overwrite_partitions.,
        write_mode: Optional[
            Literal["append", "overwrite", "overwrite_partitions"]
        ] = None,
        # If True and mode=”overwrite”, creates an archived version of the table catalog before updating it.,
        catalog_versioning: Optional[bool] = None,
        # If True allows schema evolution (new or missing columns), otherwise a exception will be raised.,
        # True by default. (Only considered if mode in (“append”, “overwrite_partitions”)),
        schema_evolution: Optional[bool] = None,
        # Glue/Athena catalog: Database name.,
        database: Optional[str] = None,
        # Create Glue/Athena database if it does not exist.
        create_database: bool = False,
        # Glue/Athena catalog: Table name.,
        table: Optional[str] = None,
        # The type of the Glue Table. Set to EXTERNAL_TABLE if None.,
        table_type: Optional[str] = None,
        # Dictionary of columns names and Athena/Glue types to be casted.,
        # Useful when you have columns with undetermined or mixed data types.,
        # (e.g. {‘col name’: ‘bigint’, ‘col2 name’: ‘int’}),
        dtype: Optional[Dict[str, str]] = None,
        # Glue/Athena catalog: Table description,
        table_description: Optional[str] = None,
        # Glue/Athena catalog: Key/value pairs to tag the table.,
        parameters: Optional[Dict[str, str]] = None,
        # Glue/Athena catalog: Columns names and the related comments,
        # (e.g. {‘col0’: ‘Column 0.’, ‘col1’: ‘Column 1.’, ‘col2’: ‘Partition.’}).,
        columns_comments: Optional[Dict[str, str]] = None,
        # regular_partitions (bool) – Create regular partitions (Non projected partitions) on Glue Catalog.,
        # Disable when you will work only with Partition Projection.,
        regular_partitions: Optional[bool] = None,
        # Enable Partition Projection on Athena,
        # https://docs.aws.amazon.com/athena/latest/ug/partition-projection.html,
        projection_enabled: Optional[bool] = None,
        # Dictionary of partitions names and Athena projections types. Valid types: “enum”, “integer”, “date”, “injected”,
        # https://docs.aws.amazon.com/athena/latest/ug/partition-projection-supported-types.html,
        # e.g. {‘col_name’: ‘enum’, ‘col2_name’: ‘integer’},
        projection_types: Optional[Dict[str, str]] = None,
        # Dictionary of partitions names and Athena projections ranges.,
        # https://docs.aws.amazon.com/athena/latest/ug/partition-projection-supported-types.html,
        # e.g. {‘col_name’: ‘0,10’, ‘col2_name’: ‘-1,8675309’},
        projection_ranges: Optional[Dict[str, str]] = None,
        # Dictionary of partitions names and Athena projections values.,
        # https://docs.aws.amazon.com/athena/latest/ug/partition-projection-supported-types.html,
        # e.g. {‘col_name’: ‘A,B,Unknown’, ‘col2_name’: ‘foo,boo,bar’},
        projection_values: Optional[Dict[str, str]] = None,
        # Dictionary of partitions names and Athena projections intervals.,
        # https://docs.aws.amazon.com/athena/latest/ug/partition-projection-supported-types.html,
        # e.g. {‘col_name’: ‘1’, ‘col2_name’: ‘5’},
        projection_intervals: Optional[Dict[str, str]] = None,
        # Dictionary of partitions names and Athena projections digits.,
        # https://docs.aws.amazon.com/athena/latest/ug/partition-projection-supported-types.html,
        # e.g. {‘col_name’: ‘1’, ‘col2_name’: ‘2’},
        projection_digits: Optional[Dict[str, str]] = None,
        # The ID of the Data Catalog from which to retrieve Databases.,
        # If none is provided, the AWS account ID is used by default.,
        catalog_id: Optional[str] = None,
        **pandas_kwargs: Any,
    ) -> bool:
        """
        Write DataFrame to S3CsvDataset.
        """

        # S3CsvDataset not yet initialized
        if self.args is None:
            return False

        if df is None:
            logger.error("DataFrame not provided")
            return False

        dataset_path = path or self.uri
        if dataset_path is None:
            logger.error("Dataset path not provided")
            return False
        logger.info(f"Writing to {dataset_path}")

        # create a dict of args which are not null
        not_null_args: Dict[str, Any] = {}

        if index is not None:
            not_null_args["index"] = index

        if columns is not None:
            not_null_args["columns"] = columns

        _sep = sep or self.sep
        if _sep is not None:
            not_null_args["sep"] = _sep

        _table = table or self.table
        if _table is not None:
            not_null_args["table"] = _table

        _database = database or self.database
        if _database is not None:
            not_null_args["database"] = _database

        _table_type = table_type or self.table_type
        if _table_type is not None:
            not_null_args["table_type"] = _table_type

        _table_description = table_description or self.table_description
        if _table_description is not None:
            not_null_args["description"] = _table_description

        _write_mode = write_mode or self.write_mode
        if _write_mode is not None:
            not_null_args["mode"] = _write_mode

        _dtype = dtype or self.dtype
        if _dtype is not None:
            not_null_args["dtype"] = _dtype

        _parameters = parameters or self.parameters
        if _parameters is not None:
            not_null_args["parameters"] = _parameters

        _columns_comments = columns_comments or self.columns_comments
        if _columns_comments is not None:
            not_null_args["columns_comments"] = _columns_comments

        _filename_prefix = filename_prefix or self.filename_prefix
        if _filename_prefix is not None:
            not_null_args["filename_prefix"] = _filename_prefix

        _partition_cols = partition_cols or self.partition_cols
        if _partition_cols is not None:
            not_null_args["partition_cols"] = _partition_cols

        _bucketing_info = bucketing_info or self.bucketing_info
        if _bucketing_info is not None:
            not_null_args["bucketing_info"] = _bucketing_info

        _concurrent_partitioning = (
            concurrent_partitioning or self.concurrent_partitioning
        )
        if _concurrent_partitioning is not None:
            not_null_args["concurrent_partitioning"] = _concurrent_partitioning

        _catalog_versioning = catalog_versioning or self.catalog_versioning
        if _catalog_versioning is not None:
            not_null_args["catalog_versioning"] = _catalog_versioning

        _schema_evolution = schema_evolution or self.schema_evolution
        if _schema_evolution is not None:
            not_null_args["schema_evolution"] = _schema_evolution

        _catalog_id = catalog_id or self.catalog_id
        if _catalog_id is not None:
            not_null_args["catalog_id"] = _catalog_id

        _use_threads = use_threads or self.use_threads
        if _use_threads is not None:
            not_null_args["use_threads"] = _use_threads

        _boto3_session = boto3_session or self.boto3_session
        if _boto3_session is not None:
            not_null_args["boto3_session"] = _boto3_session

        _s3_additional_kwargs = s3_additional_kwargs or self.s3_additional_kwargs
        if _s3_additional_kwargs is not None:
            not_null_args["s3_additional_kwargs"] = _s3_additional_kwargs

        _regular_partitions = regular_partitions  # or self.regular_partitionsl
        if _regular_partitions is not None:
            not_null_args["regular_partitions"] = _regular_partitions

        _projection_enabled = projection_enabled  # or self.projection_enabled
        if _projection_enabled is not None:
            not_null_args["projection_enabled"] = _projection_enabled

        _projection_types = projection_types  # or self.projection_types
        if _projection_types is not None:
            not_null_args["projection_types"] = _projection_types

        _projection_ranges = projection_ranges  # or self.projection_ranges
        if _projection_ranges is not None:
            not_null_args["projection_ranges"] = _projection_ranges

        _projection_values = projection_values  # or self.projection_values
        if _projection_values is not None:
            not_null_args["projection_values"] = _projection_values

        _projection_intervals = projection_intervals  # or self.projection_intervals
        if _projection_intervals is not None:
            not_null_args["projection_intervals"] = _projection_intervals

        _projection_digits = projection_digits  # or self.projection_digits
        if _projection_digits is not None:
            not_null_args["projection_digits"] = _projection_digits

        not_null_args.update(pandas_kwargs)

        try:
            import awswrangler as wr

            # Create database if needed
            if _database is not None and create_database:
                logger.info(f"Creating database: '{_database}'")
                wr.catalog.create_database(
                    name=_database,
                    exist_ok=True,
                    catalog_id=_catalog_id,
                    boto3_session=_boto3_session,
                )

            response: Dict[str, Union[List[str], Dict[str, List[str]]]] = wr.s3.to_csv(
                df=df,
                path=dataset_path,
                dataset=True,
                sanitize_columns=True,
                **not_null_args,
            )
            logger.info(f"Dataset {self.name} written to {dataset_path}")
            logger.debug(f"Response: {response}")
            logger.info("--**-- Done")
            return True
        except Exception as e:
            logger.error("Could not write to dataset: {}".format(self.name))
            raise

    def create_from_query(
        self,
        sql: str,
        # If creating from a table stored in a different database
        # origin_database is the database where the original table is stored.
        origin_database: Optional[str] = None,
        # S3 path for the dataset or use the path defined in the dataset
        path: Optional[str] = None,
        # A list of columns by which the CTAS table will be partitioned.
        partitioning_info: Optional[List[str]] = None,
        # Tuple consisting of the column names used for bucketing as the
        # first element and the number of buckets as the second element.
        # Only str, int and bool are supported as column data types for bucketing.
        bucketing_info: Optional[Tuple[List[str], int]] = None,
        # The single-character field delimiter for files in CSV, TSV, and text files.
        field_delimiter: Optional[str] = None,
        # Athena workgroup.
        workgroup: Optional[str] = None,
        # Data Source / Catalog name. If None, ‘AwsDataCatalog’ is used.
        data_source: Optional[str] = None,
        # Whether to wait for the query to finish and return a dictionary with the Query metadata.
        wait: bool = False,
        # Boto3 Session. The default boto3 Session will be used if boto3_session receive None.,
        boto3_session: Optional[Any] = None,
        # Drop the table before running CTAS query
        drop_before_create: bool = False,
    ) -> bool:
        """
        Create dataset from query
        """

        # S3CsvDataset not yet initialized
        if self.args is None:
            return False

        if sql is None:
            logger.error("Sql not provided")
            return False

        dataset_path = path or self.uri
        if dataset_path is None:
            logger.error("Dataset path not provided")
            return False
        logger.info(f"Writing to {dataset_path}")

        database = origin_database or self.database
        if database is None:
            logger.error("Database not provided")
            return False

        # create a dict of args which are not null
        not_null_args: Dict[str, Any] = {}

        _partitioning_info = partitioning_info or self.partition_cols
        if _partitioning_info is not None:
            not_null_args["partitioning_info"] = _partitioning_info

        _bucketing_info = bucketing_info or self.bucketing_info
        if _bucketing_info is not None:
            not_null_args["bucketing_info"] = _bucketing_info

        _field_delimiter = field_delimiter or self.sep
        if _field_delimiter is not None:
            not_null_args["field_delimiter"] = _field_delimiter

        if workgroup is not None:
            not_null_args["workgroup"] = workgroup

        if data_source is not None:
            not_null_args["data_source"] = data_source

        _boto3_session = boto3_session or self.boto3_session
        if _boto3_session is not None:
            not_null_args["boto3_session"] = _boto3_session

        try:
            import awswrangler as wr

            if drop_before_create:
                self.delete(path=dataset_path, boto3_session=_boto3_session)

            response: Dict[str, Union[str, Any]] = wr.athena.create_ctas_table(
                sql=sql,
                database=database,
                ctas_table=self.table,
                ctas_database=self.database,
                s3_output=dataset_path,
                storage_format="TEXTFILE",
                wait=wait,
                **not_null_args,
            )
            logger.info(f"Dataset {self.name} written to {dataset_path}")
            logger.debug(f"Response: {response}")
            logger.info("--**-- Done")
            return True
        except Exception as e:
            logger.error("Could not write to dataset: {}".format(self.name))
            raise

    ######################################################
    ## Delete DataAsset
    ######################################################

    def delete(
        self,
        # S3 path for the dataset
        path: Optional[str] = None,
        # Boto3 Session. The default boto3 Session will be used if boto3_session receive None.
        boto3_session: Optional[Any] = None,
    ) -> bool:
        import awswrangler as wr

        table_exists = wr.catalog.does_table_exist(
            table=self.table,
            database=self.database,
            catalog_id=self.catalog_id,
            boto3_session=boto3_session,
        )
        if not table_exists:
            return True

        s3_path = path or self.uri
        logger.info(f"Deleting objects at {s3_path}")
        wr.s3.delete_objects(s3_path)

        logger.info(f"Dropping table {self.name}")
        drop_table = wr.catalog.delete_table_if_exists(
            database=self.database,
            table=self.table,
            catalog_id=self.catalog_id,
            boto3_session=boto3_session,
        )
        if drop_table:
            logger.info(f"Table {self.name} dropped")
        return drop_table

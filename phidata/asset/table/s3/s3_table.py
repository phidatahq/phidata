from typing import Optional, Any, Union, List, Dict
from typing_extensions import Literal

from phidata.asset import DataAsset, DataAssetArgs
from phidata.infra.aws.resource.s3.bucket import S3Bucket
from phidata.utils.enums import ExtendedEnum
from phidata.utils.log import logger


class S3TableFormat(ExtendedEnum):
    CSV = "CSV"
    JSON = "JSON"
    PARQUET = "PARQUET"
    FEATHER = "FEATHER"


class S3TableArgs(DataAssetArgs):
    # Table Name
    name: str
    # Database for the table
    db_name: str = "default"
    # DataModel for this table
    data_model: Optional[Any] = None
    # S3 Table Format
    table_format: S3TableFormat

    # Compression style (None, snappy, gzip, zstd).
    compression: Optional[str] = None
    # Max number of rows in each file.
    # Default is None i.e. do not split the files.
    # (e.g. 33554432, 268435456)
    max_rows_by_file: Optional[int] = None
    # Additional parameters forwarded to pyarrow.
    # e.g. pyarrow_additional_kwargs={‘coerce_timestamps’: ‘ns’, ‘allow_truncated_timestamps’=False}
    pyarrow_additional_kwargs: Optional[Dict[str, Any]] = None
    write_mode: Optional[Literal["append", "overwrite", "overwrite_partitions"]] = None

    # S3 Bucket
    bucket: Optional[S3Bucket] = None
    # S3 Path
    path: Optional[str] = None
    top_level_dir: Optional[str] = "tables"
    path_prefix: Optional[str] = None
    filename_prefix: Optional[str] = None


class S3Table(DataAsset):
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
        # Compression style (None, snappy, gzip, zstd).
        compression: Optional[str] = None,
        # Max number of rows in each file.
        # Default is None i.e. do not split the files.
        # (e.g. 33554432, 268435456)
        max_rows_by_file: Optional[int] = None,
        # Additional parameters forwarded to pyarrow.
        # e.g. pyarrow_additional_kwargs={‘coerce_timestamps’: ‘ns’, ‘allow_truncated_timestamps’=False}
        pyarrow_additional_kwargs: Optional[Dict[str, Any]] = None,
        write_mode: Optional[
            Literal["append", "overwrite", "overwrite_partitions"]
        ] = None,
        # S3 Bucket
        bucket: Optional[S3Bucket] = None,
        # S3 Path
        path: Optional[str] = None,
        top_level_dir: Optional[str] = "tables",
        path_prefix: Optional[str] = None,
        filename_prefix: Optional[str] = None,
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
                db_name=db_name,
                data_model=data_model,
                table_format=table_format,
                compression=compression,
                max_rows_by_file=max_rows_by_file,
                pyarrow_additional_kwargs=pyarrow_additional_kwargs,
                write_mode=write_mode,
                bucket=bucket,
                path=path,
                top_level_dir=top_level_dir,
                path_prefix=path_prefix,
                filename_prefix=filename_prefix,
                version=version,
                enabled=enabled,
                **kwargs,
            )
        except Exception as e:
            logger.error(f"Args for {self.name} are not valid")
            raise

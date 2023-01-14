from pathlib import Path
from typing import Optional, Union, Any, Dict
from typing_extensions import Literal

from phidata.asset.local import LocalAsset, LocalAssetArgs
from phidata.utils.enums import ExtendedEnum
from phidata.utils.log import logger


class LocalFileFormat(ExtendedEnum):
    CSV = "csv"
    TSV = "tsv"
    TXT = "txt"
    JSON = "json"
    PARQUET = "parquet"
    FEATHER = "feather"


class LocalFileArgs(LocalAssetArgs):
    # File name
    name: Optional[str] = None
    # File format
    file_format: Optional[LocalFileFormat] = None

    # True If the file is located in the current dir.
    # Default: False
    current_dir: bool = False

    # Parent directory of the file relative to the storage_dir
    # Used to build the file_path
    file_dir: Optional[Union[str, Path]] = None

    # Absolute path for the file
    file_path: Optional[Path] = None


class LocalFile(LocalAsset):
    def __init__(
        self,
        # File name
        name: Optional[str] = None,
        # File format
        file_format: Optional[LocalFileFormat] = None,
        # Set as True if the file is located in the current directory.
        # By default, we store files in the storage_dir.
        # Default: False
        current_dir: bool = False,
        # Parent directory of the file relative to the storage_dir
        # Used to build the file_path
        file_dir: Optional[Union[str, Path]] = None,
        # Absolute path for the file
        file_path: Optional[Path] = None,
        version: Optional[str] = None,
        enabled: bool = True,
        **kwargs,
    ) -> None:

        super().__init__()
        try:
            self.args: LocalFileArgs = LocalFileArgs(
                name=name,
                file_format=file_format,
                current_dir=current_dir,
                file_dir=file_dir,
                file_path=file_path,
                version=version,
                enabled=enabled,
                **kwargs,
            )
        except Exception as e:
            logger.error(f"Args for {self.name} are not valid")
            raise

    @property
    def file_format(self) -> Optional[LocalFileFormat]:
        if self.args.file_format is not None:
            return self.args.file_format

        # logger.debug("-*--*- Building file_format")
        fp = self.file_path
        if fp is None:
            return None
        suffix = fp.suffix[1:]  # remove the . from ".json" or ".csv"
        # logger.debug("suffix: {}".format(suffix))

        derived_file_format: Optional[LocalFileFormat] = None
        if suffix.lower() in LocalFileFormat.values_list():
            derived_file_format = LocalFileFormat.from_str(suffix.lower())
            self.args.file_format = derived_file_format
        return self.args.file_format

    @file_format.setter
    def file_format(self, file_format: Optional[LocalFileFormat]) -> None:
        if file_format is not None:
            self.args.file_format = file_format

    @property
    def current_dir(self) -> bool:
        return self.args.current_dir if self.args else True

    @current_dir.setter
    def current_dir(self, current_dir: bool) -> None:
        if current_dir is not None:
            self.args.current_dir = current_dir

    @property
    def file_dir(self) -> Optional[Union[str, Path]]:
        return self.args.file_dir if self.args else None

    @file_dir.setter
    def file_dir(self, file_dir: Union[str, Path]) -> None:
        if file_dir is not None:
            self.args.file_dir = file_dir

    @property
    def file_path(self) -> Optional[Path]:
        if self.args.file_path is not None:
            return self.args.file_path

        logger.debug("-*--*- Building file_path")
        _file_path: Optional[Path] = None

        # Use current_dir as base path if set
        if self.current_dir:
            logger.debug("use current_dir: {}".format(self.current_dir))
            _file_path = Path(__file__).resolve()

        # Or use storage_dir_path as the base path
        if _file_path is None:
            # storage_dir_path is loaded from the current environment variable
            _file_path = self.storage_dir_path

        # Add the file_dir if available
        if self.file_dir is not None:
            if _file_path is None:
                # _file_path is None meaning no storage_dir_path
                _file_path = Path(".").resolve().joinpath(self.file_dir)
            else:
                _file_path = _file_path.joinpath(self.file_dir)

        # Add the file_name
        if self.name is not None:
            if _file_path is None:
                _file_path = Path(".").resolve().joinpath(self.name)
            else:
                _file_path = _file_path.joinpath(self.name)

        self.args.file_path = _file_path
        return self.args.file_path

    @classmethod
    def temporary(cls, name: str) -> "LocalFile":
        return cls(name=name, file_dir="tmp")

    ######################################################
    ## Write to file
    ######################################################

    def write_polars_df(
        self,
        # A polars DataFrame
        df: Optional[Any] = None,
        #
        # -*- CSV Files
        #
        # Whether to include header in the CSV output.
        include_header: Optional[bool] = None,
        # Separate CSV fields with this symbol.
        sep: Optional[str] = None,
        # Byte to use as quoting character.
        quote: Optional[str] = None,
        # Number of rows that will be processed per thread.
        batch_size: Optional[int] = None,
        datetime_format: Optional[str] = None,
        date_format: Optional[str] = None,
        time_format: Optional[str] = None,
        float_precision: Optional[int] = None,
        null_value: Optional[str] = None,
        #
        # -*- JSON Files
        #
        # Pretty serialize json.
        pretty: Optional[bool] = None,
        # Write to row oriented json. This is slower, but more common.
        row_oriented: Optional[bool] = None,
        # -*- How to behave if the file already exists.
        # fail: Raise a ValueError.
        # replace: Drop the file before inserting new values.
        # append: Insert new values to the existing table.
        if_exists: Optional[Literal["fail", "replace", "append"]] = None,
        **kwargs,
    ) -> bool:
        """
        Write Polars DataFrame to a file.
        """

        # LocalFile not yet initialized
        if self.args is None:
            return False

        # Check path is available
        if self.file_path is None:
            logger.error("FilePath invalid")
            return False

        # Validate pyarrow is installed
        try:
            import pyarrow as pa
        except ImportError:
            logger.error("PyArrow not installed")
            return False

        # Validate polars is installed
        try:
            import polars as pl  # type: ignore
        except ImportError:
            logger.error("Polars not installed")
            return False

        if df is None or not isinstance(df, pl.DataFrame):
            logger.error("DataFrame invalid")
            return False

        # Write the DataFrame to a file
        file_path: Path = self.file_path
        logger.info("Writing to file: {}".format(file_path))
        if file_path.exists():
            if if_exists == "fail":
                raise ValueError("File exists: {}".format(file_path))
            elif if_exists == "replace":
                from phidata.utils.filesystem import delete_from_fs

                logger.debug("Deleting: {}".format(file_path))
                delete_from_fs(file_path)

        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            logger.debug("Format: {}".format(self.file_format))
            if self.file_format == LocalFileFormat.CSV:
                # Create a dict of args which are not null
                csv_args: Dict[str, Any] = {}
                if include_header is not None:
                    csv_args["include_header"] = include_header
                if sep is not None:
                    csv_args["sep"] = sep
                if quote is not None:
                    csv_args["quote"] = quote
                if batch_size is not None:
                    csv_args["batch_size"] = batch_size
                if datetime_format is not None:
                    csv_args["datetime_format"] = datetime_format
                if date_format is not None:
                    csv_args["date_format"] = date_format
                if time_format is not None:
                    csv_args["time_format"] = time_format
                if float_precision is not None:
                    csv_args["float_precision"] = float_precision
                if null_value is not None:
                    csv_args["null_value"] = null_value

                df.write_csv(file_path, **csv_args)  # type: ignore
            elif self.file_format == LocalFileFormat.JSON:
                # Create a dict of args which are not null
                json_args: Dict[str, Any] = {}
                if include_header is not None:
                    json_args["pretty"] = pretty
                if sep is not None:
                    json_args["row_oriented"] = row_oriented

                df.write_json(file_path, **json_args)  # type: ignore
            else:
                logger.error(f"FileFormat: {self.file_format} not yet supported")
                return False
            return True
        except Exception as e:
            logger.error("Could not write to: {}".format(file_path))
            raise

    def write_pandas_df(
        self,
        df: Any = None,
        # How to behave if the file already exists.
        # fail: Raise a ValueError.
        # replace: Drop the file before inserting new values.
        # append: Insert new values to the existing table.
        if_exists: Optional[Literal["fail", "replace", "append"]] = None,
        **kwargs,
    ) -> bool:
        """
        Write DataFrame to file.
        """

        # LocalFile not yet initialized
        if self.args is None:
            return False

        # Check path is available
        if self.file_path is None:
            logger.error("FilePath invalid")
            return False

        # Validate pandas is installed
        try:
            import pandas as pd
        except ImportError:
            logger.error("Pandas not installed")
            return False

        if df is None or not isinstance(df, pd.DataFrame):
            logger.error("DataFrame invalid")
            return False

        file_path: Path = self.file_path
        logger.info("Writing to file: {}".format(file_path))
        mode: str = "w"
        if file_path.exists():
            if if_exists == "fail":
                raise ValueError("LocalFile already exists: {}".format(file_path))
            elif if_exists == "replace":
                from phidata.utils.filesystem import delete_from_fs

                logger.debug("Deleting: {}".format(file_path))
                delete_from_fs(file_path)
            elif if_exists == "append":
                mode = "a"

        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            file_path.touch(exist_ok=True)
            with file_path.open(mode) as open_file:
                logger.debug("file_format: {}".format(self.file_format))
                if self.file_format == LocalFileFormat.JSON:
                    df.to_json(open_file, orient="index", indent=4)
                elif self.file_format == LocalFileFormat.CSV:
                    df.to_csv(open_file)
                else:
                    logger.error(
                        f"LocalFileFormat: {self.file_format} not yet supported"
                    )
                    return False
            return True
        except Exception as e:
            logger.error("Could not write to: {}".format(file_path))
            raise

    def download_url(self, url: str) -> bool:
        # LocalFile not yet initialized
        if self.args is None:
            return False

        import httpx
        import rich.progress

        file_path: Optional[Path] = self.file_path
        if file_path is None:
            logger.error("FilePath not available")
            return False
        file_dir: Path = file_path.parent.resolve()

        # Download URL contents
        logger.info("Downloading")
        logger.info(f"  Url: {url}")
        logger.info(f"  To : {file_path}")

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
                        logger.warning(
                            f"Could not get total bytes_to_download from headers"
                        )

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

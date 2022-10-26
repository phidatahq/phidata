from pathlib import Path
from typing import Optional, Union, Any
from typing_extensions import Literal

from phidata.asset import DataAsset, DataAssetArgs
from phidata.utils.enums import ExtendedEnum
from phidata.utils.log import logger


class FileType(ExtendedEnum):
    CSV = "CSV"
    TSV = "TSV"
    TXT = "TXT"
    JSON = "JSON"


class FileArgs(DataAssetArgs):
    name: Optional[str] = None
    file_type: Optional[FileType] = None

    # If the file is located in the current dir.
    # Default: True
    # Used to build the file_path
    current_dir: bool = False

    # Parent directory of the file relative to the storage_dir
    # Used to build the file_path
    file_dir: Optional[Union[str, Path]] = None

    # Absolute path for the file
    file_path: Optional[Path] = None


class File(DataAsset):
    def __init__(
        self,
        name: Optional[str] = None,
        file_type: Optional[FileType] = None,
        # If the file is located in the current dir.
        # Default: False
        # Used to build the file_path
        current_dir: bool = False,
        # Parent directory of the file relative to the storage_dir
        # Used to build the file_path
        file_dir: Optional[Union[str, Path]] = None,
        # Absolute path for the file
        file_path: Optional[Path] = None,
        version: Optional[str] = None,
        enabled: bool = True,
    ) -> None:

        super().__init__()
        try:
            self.args: FileArgs = FileArgs(
                name=name,
                file_type=file_type,
                current_dir=current_dir,
                file_dir=file_dir,
                file_path=file_path,
                version=version,
                enabled=enabled,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    @property
    def file_type(self) -> Optional[FileType]:
        if self.args.file_type is not None:
            return self.args.file_type

        # logger.debug("-*--*- Building file_type")
        fp = self.file_path
        if fp is None:
            return None
        suffix = fp.suffix[1:]  # remove the . from ".json" or ".csv"
        # logger.debug("suffix: {}".format(suffix))

        derived_file_type: Optional[FileType] = None
        if suffix.upper() in FileType.values_list():
            derived_file_type = FileType.from_str(suffix.upper())
            self.args.file_type = derived_file_type
        return self.args.file_type

    @file_type.setter
    def file_type(self, file_type: Optional[FileType]) -> None:
        if file_type is not None:
            self.args.file_type = file_type

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
    def temporary(cls, name: str) -> "File":
        return cls(name=name, file_dir="tmp")

    ######################################################
    ## Write to file
    ######################################################

    def write_pandas_df(
        self,
        df: Any = None,
        # How to behave if the file already exists.
        # fail: Raise a ValueError.
        # replace: Drop the file before inserting new values.
        # append: Insert new values to the existing table.
        if_exists: Optional[Literal["fail", "replace", "append"]] = None,
    ) -> bool:
        """
        Write DataFrame to file.
        """

        # File not yet initialized
        if self.args is None:
            return False

        # Check path is available
        if self.file_path is None:
            logger.error("FilePath invalid")
            return False

        # write to file
        import pandas as pd

        if df is None or not isinstance(df, pd.DataFrame):
            logger.error("DataFrame invalid")
            return False

        file_path: Path = self.file_path
        logger.info("Writing to file: {}".format(file_path))
        mode: str = "w"
        if file_path.exists():
            if if_exists == "fail":
                raise ValueError("File already exists: {}".format(file_path))
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
                logger.debug("file_type: {}".format(self.file_type))
                if self.file_type == FileType.JSON:
                    df.to_json(open_file, orient="index", indent=4)
                elif self.file_type == FileType.CSV:
                    df.to_csv(open_file)
                else:
                    logger.error(f"FileType: {self.file_type} not yet supported")
                    return False
            return True
        except Exception as e:
            logger.error("Could not write to: {}".format(file_path))
            raise

    def download_url(self, url: str) -> bool:
        # File not yet initialized
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

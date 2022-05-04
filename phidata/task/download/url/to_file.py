from pathlib import Path
from typing import Optional

from pydantic import AnyUrl

from phidata.asset.file import File
from phidata.utils.cli_console import print_info, print_error, print_warning
from phidata.utils.log import logger
from phidata.task import PythonTask, PythonTaskArgs


class DownloadUrlToFileArgs(PythonTaskArgs):
    file: File
    url: str


class DownloadUrlToFile(PythonTask):
    def __init__(
        self,
        file: File,
        url: str,
        name: str = "download_url_to_file",
        task_id: Optional[str] = None,
        dag_id: Optional[str] = None,
        version: Optional[str] = None,
        enabled: bool = True,
    ):
        super().__init__()
        try:
            self.args: DownloadUrlToFileArgs = DownloadUrlToFileArgs(
                file=file,
                url=url,
                name=name,
                task_id=task_id,
                dag_id=dag_id,
                version=version,
                enabled=enabled,
                entrypoint=download_url_to_file,
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
    def url(self) -> str:
        return self.args.url

    @url.setter
    def url(self, url: str) -> None:
        if url is not None:
            self.args.url = url


def download_url_to_file(**kwargs) -> bool:

    import httpx
    import rich.progress

    args = DownloadUrlToFileArgs.from_kwargs(kwargs)
    # logger.info(f"DownloadUrlToFileArgs: {args}")

    file_to_load: Optional[File] = args.file
    if file_to_load is None:
        print_error("File not available")
        return False
    file_path: Optional[Path] = file_to_load.file_path
    if file_path is None:
        print_error("FilePath not available")
        return False
    file_dir: Path = file_path.parent.resolve()

    url = args.url
    if url is None:
        print_error("URL not available")
        return False

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
        print_error("Could not download url, please try again")
        print_info("--- stacktrace ---")
        logger.exception(e)
        print_info("--- stacktrace ---")
    return False


def best_guess_file_name(url: AnyUrl, file_name: Optional[str] = None) -> Optional[str]:

    from phidata.utils.dttm import get_today_utc_date_str

    fn: Optional[str] = file_name
    if fn is None:
        _url_path: str = str(url)
        if "/" in _url_path:
            fn = _url_path.split("/")[-1]
    if fn is None:
        fn = get_today_utc_date_str()
    # logger.debug("fn: {}".format(fn))
    return fn

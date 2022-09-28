from typing import Optional, Literal

from phidata.asset.file import File
from phidata.asset.aws.s3.object import S3Object
from phidata.utils.log import logger
from phidata.task import PythonTask, PythonTaskArgs


class DownloadUrlToS3Args(PythonTaskArgs):
    url: str
    s3_object: S3Object
    # How to behave if the object already exists.
    # fail: Raise a ValueError.
    # replace: Replace the object
    # skip: Do nothing
    if_exists: Literal["fail", "replace", "skip"] = "replace"
    # Optional File object to use
    file: Optional[File] = None


class DownloadUrlToS3(PythonTask):
    def __init__(
        self,
        url: str,
        s3_object: S3Object,
        if_exists: Literal["fail", "replace", "append"] = "replace",
        file: Optional[File] = None,
        name: str = "download_url_to_s3",
        task_id: Optional[str] = None,
        dag_id: Optional[str] = None,
        version: Optional[str] = None,
        enabled: bool = True,
    ):
        super().__init__()
        try:
            self.args: DownloadUrlToS3Args = DownloadUrlToS3Args(
                url=url,
                s3_object=s3_object,
                if_exists=if_exists,
                file=file,
                name=name,
                task_id=task_id,
                dag_id=dag_id,
                version=version,
                enabled=enabled,
                entrypoint=download_url_to_s3,
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
    def s3_object(self) -> Optional[S3Object]:
        return self.args.s3_object

    @s3_object.setter
    def s3_object(self, s3_object: S3Object) -> None:
        if s3_object is not None:
            self.args.s3_object = s3_object

    @property
    def if_exists(self) -> Literal["fail", "replace", "skip"]:
        return self.args.if_exists if self.args else "skip"

    @if_exists.setter
    def if_exists(self, if_exists: Literal["fail", "replace", "skip"]) -> None:
        if if_exists is not None:
            self.args.if_exists = if_exists

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


def download_url_to_s3(**kwargs) -> bool:

    args: DownloadUrlToS3Args = DownloadUrlToS3Args.from_kwargs(kwargs)
    # logger.info(f"DownloadUrlToS3Args: {args}")

    if args.url is None:
        logger.error("URL not available")
        return False

    if args.s3_object is None:
        logger.error("S3Object not available")
        return False

    if args.file is None:
        args.file = File.temporary(best_guess_file_name(args.url))

    download_success = args.file.download_url(args.url)
    if download_success:
        return args.s3_object.upload_file(file=args.file, if_exists=args.if_exists)
    return False

from typing import Optional

from phidata.asset.file import File
from phidata.asset.aws.s3.object import S3Object
from phidata.utils.log import logger
from phidata.task import PythonTask, PythonTaskArgs


class UploadFileToS3Args(PythonTaskArgs):
    file: File
    s3_object: S3Object


class UploadFileToS3(PythonTask):
    def __init__(
        self,
        file: File,
        s3_object: S3Object,
        name: str = "upload_file_to_s3",
        task_id: Optional[str] = None,
        dag_id: Optional[str] = None,
        version: Optional[str] = None,
        enabled: bool = True,
    ):
        super().__init__()
        try:
            self.args: UploadFileToS3Args = UploadFileToS3Args(
                file=file,
                s3_object=s3_object,
                name=name,
                task_id=task_id,
                dag_id=dag_id,
                version=version,
                enabled=enabled,
                entrypoint=upload_file_to_s3_object,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    @property
    def file(self) -> File:
        return self.args.file

    @file.setter
    def file(self, file: File) -> None:
        if file is not None:
            self.args.file = file

    @property
    def s3_object(self) -> S3Object:
        return self.args.s3_object

    @s3_object.setter
    def s3_object(self, s3_object: S3Object) -> None:
        if s3_object is not None:
            self.args.s3_object = s3_object


def upload_file_to_s3_object(**kwargs) -> bool:

    args: UploadFileToS3Args = UploadFileToS3Args(**kwargs)
    # logger.debug("UploadFileToS3Args: {}".format(args))

    if args.file is None:
        logger.error("File not available")
        return False

    if args.s3_object is None:
        logger.error("S3Object not available")
        return False

    upload_success = args.s3_object.upload_file(file=args.file)
    return upload_success

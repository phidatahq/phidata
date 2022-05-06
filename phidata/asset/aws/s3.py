from pathlib import Path
from typing import Optional, Literal

from phidata.asset.file import File
from phidata.asset import DataAsset, DataAssetArgs
from phidata.infra.aws.resource.s3.bucket import S3Bucket
from phidata.utils.log import logger


class S3ObjectArgs(DataAssetArgs):
    key: str
    bucket: S3Bucket


class S3Object(DataAsset):
    def __init__(
        self,
        key: str,
        bucket: S3Bucket,
        version: Optional[str] = None,
        enabled: bool = True,
    ) -> None:

        super().__init__()
        try:
            self.args: S3ObjectArgs = S3ObjectArgs(
                key=key,
                bucket=bucket,
                name=key,
                version=version,
                enabled=enabled,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    @property
    def key(self) -> str:
        return self.args.key

    @key.setter
    def key(self, key: str) -> None:
        if key is not None:
            self.args.key = key

    @property
    def bucket(self) -> S3Bucket:
        return self.args.bucket

    @bucket.setter
    def bucket(self, bucket: S3Bucket) -> None:
        if bucket is not None:
            self.args.bucket = bucket

    @property
    def uri(self) -> str:
        return f"s3://{self.bucket.name}/{self.key}"

    ######################################################
    ## Write to s3
    ######################################################

    def upload_file(
        self,
        file: File,
        if_exists: Optional[Literal["fail", "replace", "skip"]] = "skip",
    ) -> bool:

        ######################################################
        ## Validate
        ######################################################

        # S3Object not yet initialized
        if self.args is None:
            return False

        # Check file_path is available
        file_path: Optional[Path] = file.file_path
        if file_path is None or not isinstance(file_path, Path):
            logger.error("FilePath invalid")
            return False

        bucket_name = self.bucket.name
        object_key = self.args.key
        logger.info("Uploading")
        logger.info(f"  File: {file_path}")
        logger.info(f"  To  : {bucket_name}/{object_key}")

        ######################################################
        ## Upload
        ######################################################
        try:
            from botocore.exceptions import ClientError

            s3_bucket = self.bucket.read()
            # logger.info("Bucket: {}".format(s3_bucket))
            # logger.info("Bucket type: {}".format(type(s3_bucket)))

            if s3_bucket is None:
                logger.error(
                    f"Could not reach bucket: {bucket_name}. Please confirm it exists."
                )
                return False

            # upload file to bucket
            s3_object_size = 0
            s3_object = s3_bucket.Object(key=object_key)
            try:
                s3_object.load()
                s3_object_size = s3_object.content_length
                # logger.info("s3_object_size: {}".format(s3_object_size))
            except ClientError as e:
                pass

            # if object exists
            if s3_object_size >= 1:
                logger.info(f"Object {bucket_name}/{object_key} exists")

                if if_exists == "skip":
                    return True

                if if_exists == "fail":
                    raise ValueError(
                        f"Object {bucket_name}/{object_key} already exists"
                    )

            # logger.info("s3_object type: {}".format(type(s3_object)))
            # logger.info("s3_object: {}".format(s3_object))
            logger.info("Uploading S3Object")
            s3_object.upload_file(Filename=str(file_path.resolve()))
            logger.info("S3Object uploaded")
            return True
        except Exception as e:
            logger.error("Could not upload S3Object, please try again")
            logger.exception(e)
        return False

    ######################################################
    ## Read from s3
    ######################################################

    def download_file(self, file: File) -> bool:
        """

        :param file:
        :return:

        TODO: add params to this function using
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/customizations/s3.html#boto3.s3.transfer.TransferConfig
        """

        ######################################################
        ## Validate
        ######################################################

        # S3Object not yet initialized
        if self.args is None:
            return False

        # Check file_path is available
        file_path: Optional[Path] = file.file_path
        if file_path is None or not isinstance(file_path, Path):
            logger.error("FilePath invalid")
            return False

        bucket_name = self.bucket.name
        object_key = self.args.key
        logger.info("Download")
        logger.info(f"  Object : {bucket_name}/{object_key}")
        logger.info(f"  To     : {file_path}")

        ######################################################
        ## Download
        ######################################################
        try:
            from botocore.exceptions import ClientError

            s3_bucket = self.bucket.read()
            # logger.info("Bucket: {}".format(s3_bucket))
            # logger.info("Bucket type: {}".format(type(s3_bucket)))

            if s3_bucket is None:
                logger.error(
                    f"Could not reach bucket: {bucket_name}. Please confirm it exists."
                )
                return False

            # download object to file
            s3_object_size = 0
            s3_object = s3_bucket.Object(key=object_key)
            try:
                s3_object.load()
                s3_object_size = s3_object.content_length
                logger.debug("s3_object_size: {}".format(s3_object_size))
            except ClientError as e:
                pass
            if s3_object_size == 0:
                logger.info(f"Object {bucket_name}/{object_key} does not exist")
                return False

            logger.info("Download S3Object to File")
            # create parent dir if need
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Object.download_file
            s3_object.download_file(Filename=str(file_path.resolve()))
            logger.info("S3Object downloaded")
            return True
        except Exception as e:
            logger.error("Could not download S3Object, please try again")
            logger.exception(e)
        return False

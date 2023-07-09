from typing import Optional, Any

from phi.utils.log import logger


class AwsApiClient:
    def __init__(
        self,
        aws_region: Optional[str] = None,
        aws_profile: Optional[str] = None,
    ):
        super().__init__()
        self.aws_region: Optional[str] = aws_region
        self.aws_profile: Optional[str] = aws_profile

        # aws boto3 session
        self._boto3_session: Optional[Any] = None
        logger.debug("**-+-** AwsApiClient created")

    def create_boto3_session(self) -> Optional[Any]:
        """Create a boto3 session"""
        from boto3 import session as boto3_session

        logger.debug("Creating boto3.Session")
        session = None
        try:
            session = boto3_session.Session(
                region_name=self.aws_region,
                profile_name=self.aws_profile,
            )
            logger.debug("**-+-** boto3.Session created")
            logger.debug(f"\taws_region: {session.region_name}")
            logger.debug(f"\taws_profile: {session.profile_name}")
        except Exception:
            raise
        return session

    @property
    def boto3_session(self) -> Optional[Any]:
        if self._boto3_session is None:
            self._boto3_session = self.create_boto3_session()
        return self._boto3_session

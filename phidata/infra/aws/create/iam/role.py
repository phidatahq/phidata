import json
from typing import List, Optional, Dict, Any

from phidata.infra.aws.resource.iam.role import IamRole, IamPolicy
from phidata.infra.aws.resource.s3.bucket import S3Bucket


def create_glue_iam_policy(
    name: str = "glueS3CrawlerPolicy",
    version: str = "2022-04-26",
    s3_buckets: Optional[List[S3Bucket]] = None,
) -> IamPolicy:
    statements: List[Dict[str, Any]] = []
    if s3_buckets is not None:
        statements.append(
            {
                "Effect": "Allow",
                "Action": ["s3:ListBucket"],
                "Resource": [f"arn:aws:s3:::{bucket.name}" for bucket in s3_buckets],
            }
        )
        statements.append(
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket.name}/*" for bucket in s3_buckets],
            }
        )
    else:
        statements.append(
            {
                "Effect": "Allow",
                "Action": ["s3:ListBucket"],
                "Resource": ["arn:aws:s3:::*"],
            }
        )
        statements.append(
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject"],
                "Resource": ["arn:aws:s3:::*/*"],
            }
        )

    return IamPolicy(
        name=name,
        policy_document=json.dumps(
            {
                "Version": version,
                "Statement": statements,
            }
        ),
    )


def create_glue_iam_role(
    name: str,
    s3_buckets: Optional[List[S3Bucket]] = None,
    iam_policy_name: str = "glueS3CrawlerPolicy",
    iam_policy_version: str = "2022-04-26",
    skip_create: bool = False,
    skip_delete: bool = False,
) -> IamRole:

    iam_policy = create_glue_iam_policy(
        name=iam_policy_name, version=iam_policy_version, s3_buckets=s3_buckets
    )
    return IamRole(
        name=name,
        assume_role_policy_document=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "glue.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
        ),
        policies=[iam_policy],
        policy_arns=["arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"],
        skip_create=skip_create,
        skip_delete=skip_delete,
    )

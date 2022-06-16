import json
from typing import List, Optional

from phidata.infra.aws.resource.iam.role import IamRole, IamPolicy


def create_assume_eks_admin_role_policy(
    account_id: str,
    eks_admin_role: IamRole,
    name: Optional[str] = "assume-eks-admin-role.policy",
    version: Optional[str] = "2012-10-17",
    skip_create: bool = False,
    skip_delete: bool = False,
) -> IamPolicy:
    return IamPolicy(
        name=name,
        policy_document=json.dumps(
            {
                "Version": version,
                "Statement": [
                    {
                        "Sid": "VisualEditor0",
                        "Effect": "Allow",
                        "Action": "sts:AssumeRole",
                        "Resource": f"arn:aws:iam::{account_id}:role/{eks_admin_role.name}",
                    }
                ],
            }
        ),
        skip_create=skip_create,
        skip_delete=skip_delete,
    )


def create_eks_admin_policy(
    account_id: str,
    name: Optional[str] = "eks-admin.policy",
    version: Optional[str] = "2012-10-17",
    skip_create: bool = False,
    skip_delete: bool = False,
) -> IamPolicy:
    return IamPolicy(
        name=name,
        policy_document=json.dumps(
            {
                "Version": version,
                "Statement": [
                    {
                        "Sid": "VisualEditor0",
                        "Effect": "Allow",
                        "Action": [
                            "eks:ListClusters",
                            "eks:DescribeAddonVersions",
                            "eks:CreateCluster",
                        ],
                        "Resource": "*",
                    },
                    {
                        "Sid": "VisualEditor1",
                        "Effect": "Allow",
                        "Action": "eks:*",
                        "Resource": f"arn:aws:eks:*:{account_id}:cluster/*",
                    },
                ],
            }
        ),
        skip_create=skip_create,
        skip_delete=skip_delete,
    )


def create_eks_admin_role(
    account_id: str,
    name: Optional[str] = "eks-admin.role",
    version: Optional[str] = "2012-10-17",
    iam_policy_name: Optional[str] = "eks-admin.policy",
    extra_policy_arns: Optional[List[str]] = None,
    skip_create: bool = False,
    skip_delete: bool = False,
) -> IamRole:

    eks_admin_iam_policy = create_eks_admin_policy(
        account_id=account_id,
        name=iam_policy_name,
        version=version,
        skip_create=skip_create,
        skip_delete=skip_delete,
    )
    return IamRole(
        name=name,
        assume_role_policy_document=json.dumps(
            {
                "Version": version,
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": f"arn:aws:iam::{account_id}:root"},
                        "Action": "sts:AssumeRole",
                        "Condition": {},
                    }
                ],
            }
        ),
        policies=[eks_admin_iam_policy],
        policy_arns=extra_policy_arns,
        skip_create=skip_create,
        skip_delete=skip_delete,
    )

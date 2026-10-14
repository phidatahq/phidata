"""Deploy or remove an AgentCore Runtime for sandbox sessions. This creates AWS resources.

Builds the ARM64 image from Dockerfile.agentcore, pushes it to a new ECR
repository, creates an execution role and a PUBLIC runtime without session
storage, then prints the runtime ARN to pass as the sandbox image.

  .venv/bin/python cookbook/frameworks/sandbox/agentcore_setup.py deploy --name agno-sandbox
  .venv/bin/python cookbook/frameworks/sandbox/agentcore_setup.py teardown --name agno-sandbox

Every resource carries the given name. Set AWS_PROFILE and AWS_REGION first.
The role may call Bedrock models, so a Claude harness needs no API key.
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import boto3


def deploy(session: boto3.session.Session, name: str, tag: str) -> None:
    region = session.region_name
    account = session.client("sts").get_caller_identity()["Account"]
    ecr, iam = session.client("ecr"), session.client("iam")
    control = session.client("bedrock-agentcore-control")

    try:
        repository = ecr.create_repository(repositoryName=name)["repository"]
    except ecr.exceptions.RepositoryAlreadyExistsException:
        repository = ecr.describe_repositories(repositoryNames=[name])["repositories"][
            0
        ]
    image = repository["repositoryUri"] + ":" + tag
    subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("build_image.py")),
            "--dockerfile",
            "Dockerfile.agentcore",
            "--platform",
            "linux/arm64",
            "--tag",
            image,
        ],
        check=True,
    )
    auth = ecr.get_authorization_token()["authorizationData"][0]
    user, password = base64.b64decode(auth["authorizationToken"]).decode().split(":", 1)
    subprocess.run(
        [
            "docker",
            "login",
            "--username",
            user,
            "--password-stdin",
            auth["proxyEndpoint"],
        ],
        input=password.encode(),
        check=True,
        capture_output=True,
    )
    subprocess.run(["docker", "push", image], check=True)

    trust = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {"aws:SourceAccount": account},
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account}:*"
                    },
                },
            }
        ],
    }
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
                "Resource": repository["repositoryArn"],
            },
            {"Effect": "Allow", "Action": "ecr:GetAuthorizationToken", "Resource": "*"},
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                "Resource": f"arn:aws:logs:{region}:{account}:log-group:/aws/bedrock-agentcore/runtimes/*",
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:CountTokens",
                ],
                "Resource": [
                    "arn:aws:bedrock:*::foundation-model/*",
                    "arn:aws:bedrock:*:*:inference-profile/*",
                ],
            },
        ],
    }
    try:
        role = iam.create_role(
            RoleName=name, AssumeRolePolicyDocument=json.dumps(trust)
        )["Role"]["Arn"]
    except iam.exceptions.EntityAlreadyExistsException:
        role = iam.get_role(RoleName=name)["Role"]["Arn"]
    iam.put_role_policy(
        RoleName=name, PolicyName=name, PolicyDocument=json.dumps(policy)
    )

    runtime_name = name.replace("-", "_")
    config = dict(
        agentRuntimeArtifact={"containerConfiguration": {"containerUri": image}},
        roleArn=role,
        networkConfiguration={"networkMode": "PUBLIC"},
        # The provider bounds each allocation itself; these are the outer limits.
        lifecycleConfiguration={"idleRuntimeSessionTimeout": 900, "maxLifetime": 3600},
    )
    existing = [
        r
        for r in control.list_agent_runtimes()["agentRuntimes"]
        if r["agentRuntimeName"] == runtime_name
    ]
    for attempt in range(12):
        try:
            if existing:
                runtime_id = existing[0]["agentRuntimeId"]
                control.update_agent_runtime(agentRuntimeId=runtime_id, **config)
            else:
                runtime_id = control.create_agent_runtime(
                    agentRuntimeName=runtime_name, **config
                )["agentRuntimeId"]
            break
        except control.exceptions.ValidationException as error:
            # A new role takes a few seconds to become assumable.
            if "Role validation failed" not in str(error) or attempt == 11:
                raise
            time.sleep(5)
    while True:
        runtime = control.get_agent_runtime(agentRuntimeId=runtime_id)
        if runtime["status"] not in ("CREATING", "UPDATING"):
            break
        time.sleep(5)
    if runtime["status"] != "READY":
        raise SystemExit(
            f"Runtime is {runtime['status']}: {runtime.get('failureReason')}"
        )
    print("Runtime ARN:", runtime["agentRuntimeArn"])


def teardown(session: boto3.session.Session, name: str) -> None:
    control, iam, ecr = (
        session.client(s) for s in ("bedrock-agentcore-control", "iam", "ecr")
    )
    for runtime in control.list_agent_runtimes()["agentRuntimes"]:
        if runtime["agentRuntimeName"] == name.replace("-", "_"):
            control.delete_agent_runtime(agentRuntimeId=runtime["agentRuntimeId"])
            print("Deleted runtime", runtime["agentRuntimeArn"])
    try:
        iam.delete_role_policy(RoleName=name, PolicyName=name)
        iam.delete_role(RoleName=name)
        print("Deleted role", name)
    except iam.exceptions.NoSuchEntityException:
        pass
    try:
        ecr.delete_repository(repositoryName=name, force=True)
        print("Deleted repository", name)
    except ecr.exceptions.RepositoryNotFoundException:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("action", choices=("deploy", "teardown"))
    parser.add_argument("--name", default="agno-sandbox")
    parser.add_argument(
        "--tag",
        default=str(int(time.time())),
        help="A new tag makes AgentCore pull a new version",
    )
    args = parser.parse_args()
    session = boto3.session.Session(region_name=os.environ.get("AWS_REGION"))
    if args.action == "deploy":
        deploy(session, args.name, args.tag)
    else:
        teardown(session, args.name)


if __name__ == "__main__":
    main()

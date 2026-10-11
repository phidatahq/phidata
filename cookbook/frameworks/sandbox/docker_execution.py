"""Run without model credentials: python cookbook/frameworks/sandbox/docker_execution.py."""

import os
from uuid import uuid4

from agno.sandbox import SandboxSpec
from agno.sandbox.docker import DockerSandboxProvider

provider = DockerSandboxProvider(namespace="cookbook-" + uuid4().hex)
computer = provider.create(
    SandboxSpec(
        agent_id="coder",
        session_id="example",
        generation=1,
        image=os.environ.get("AGNO_SANDBOX_IMAGE", "python:3.12-slim"),
        memory_mb=256,
    )
)
try:
    result = provider.exec(
        computer,
        [
            "python",
            "-c",
            "from pathlib import Path; Path('hello.txt').write_text('hello')",
        ],
    )
    assert result.exit_code == 0, result.stderr
    result = provider.exec(computer, ["cat", "hello.txt"])
    assert result.stdout == "hello"
    assert (
        provider.create(
            SandboxSpec(
                "coder",
                "example",
                1,
                os.environ.get("AGNO_SANDBOX_IMAGE", "python:3.12-slim"),
                memory_mb=256,
            )
        ).provider_ref
        == computer.provider_ref
    )
    print("Created and reused a sandbox, wrote and read a workspace file.")
finally:
    provider.destroy(computer)

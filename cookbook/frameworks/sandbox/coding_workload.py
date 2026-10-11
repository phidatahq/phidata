"""Clone, edit, test and run an application, then restore it on replacement compute.

Uses Docker and the pinned runtime image, with no network or model calls. This
exercises provider/checkpoint infrastructure; AgentOS queue acceptance is covered
by agentos.py and the integration suite.
"""

import os
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from agno.sandbox import SandboxSpec
from agno.sandbox.checkpoint import FileCheckpointStore
from agno.sandbox.docker import DockerSandboxProvider
from agno.sandbox.transfer import DockerCheckpointTransfer


def main() -> None:
    provider = DockerSandboxProvider("coding-workload-" + uuid4().hex)
    spec = SandboxSpec(
        "coder",
        "acceptance",
        1,
        os.environ.get("AGNO_TEST_RUNTIME_IMAGE", "agno-sandbox:local"),
        memory_mb=512,
        workspace_mb=128,
    )
    script = Path(__file__).with_name("workload_fixture.py").read_text()
    handles = []
    try:
        with TemporaryDirectory() as directory:
            transfer = DockerCheckpointTransfer(
                provider, FileCheckpointStore(Path(directory) / "objects")
            )
            first = provider.create(spec)
            handles.append(first)
            ready = provider.exec(first, ["mkdir", "-p", "/runtime/native"])
            assert ready.exit_code == 0, ready
            result = provider.exec(
                first, ["python", "-c", script, "prepare"], timeout=90
            )
            assert result.exit_code == 0, result
            print(result.stdout.strip())
            checkpoint = transfer.capture(
                first, state={"fixture": "coding-workload-v1"}
            )
            provider.destroy(first)
            assert provider.get(first.provider_ref) is None
            second = provider.create(replace(spec, generation=2))
            handles.append(second)
            assert transfer.restore(second, checkpoint) == {
                "fixture": "coding-workload-v1"
            }
            result = provider.exec(
                second, ["python", "-c", script, "verify"], timeout=30
            )
            assert result.exit_code == 0, result
            print(result.stdout.strip())
            print("Verified checkpoint:", checkpoint.sha256)
    finally:
        for handle in handles:
            provider.destroy(handle)


if __name__ == "__main__":
    main()

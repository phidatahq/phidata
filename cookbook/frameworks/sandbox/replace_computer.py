"""Clone/edit/test, checkpoint, destroy compute and restore without model calls."""

import os
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from agno.sandbox import SandboxSpec
from agno.sandbox.checkpoint import FileCheckpointStore
from agno.sandbox.docker import DockerSandboxProvider
from agno.sandbox.transfer import DockerCheckpointTransfer

provider = DockerSandboxProvider(namespace="recovery-cookbook-" + uuid4().hex)
spec = SandboxSpec(
    "coder",
    "example",
    1,
    os.environ.get("AGNO_SANDBOX_IMAGE", "agno-sandbox:local"),
    memory_mb=512,
)
first = provider.create(spec)
second = None
try:
    setup = """
import os, subprocess
from pathlib import Path
source = Path('/tmp/source')
source.mkdir()
(source / 'app.py').write_text('def add(a, b): return 0\\n')
(source / 'test_app.py').write_text('import unittest\\nfrom app import add\\nclass TestApp(unittest.TestCase):\\n def test_add(self): self.assertEqual(add(2, 3), 5)\\n')
(source / '.gitignore').write_text('ignored.txt\\n__pycache__/\\n')
subprocess.run(['git', 'init', '--quiet', str(source)], check=True)
subprocess.run(['git', '-C', str(source), 'add', '.'], check=True)
subprocess.run(['git', '-C', str(source), '-c', 'user.name=Sandbox Example', '-c', 'user.email=sandbox@example.invalid', 'commit', '--quiet', '-m', 'fixture'], check=True, env={**os.environ, 'GIT_AUTHOR_DATE':'2026-01-01T00:00:00Z', 'GIT_COMMITTER_DATE':'2026-01-01T00:00:00Z'})
subprocess.run(['git', 'clone', '--quiet', str(source), '/workspace/project'], check=True)
project = Path('/workspace/project')
(project / 'app.py').write_text('def add(a, b): return a + b\\n')
(project / 'ignored.txt').write_text('keep ignored data')
(project / 'notes.txt').write_text('keep untracked data')
(project / 'artifact.txt').write_text('test report')
native = Path('/runtime/native/codex')
native.mkdir(parents=True)
(native / 'thread.jsonl').write_text('{"fact":"remember this"}\\n')
(native / 'auth.json').write_text('excluded fixture credential')
"""
    result = provider.exec(first, ["python", "-c", setup])
    assert result.exit_code == 0, result.stderr
    result = provider.exec(
        first, ["python", "-m", "unittest", "discover", "-s", "project", "-v"]
    )
    assert result.exit_code == 0, result.stderr

    with TemporaryDirectory(prefix="agno-recovery-demo-") as directory:
        store = FileCheckpointStore(Path(directory) / "objects")
        transfer = DockerCheckpointTransfer(provider, store)
        reference = transfer.capture(
            first, state={"run_id": "example", "conversation": ["remember this"]}
        )
        provider.destroy(first)
        second = provider.create(replace(spec, generation=2))
        state = transfer.restore(second, reference)
        assert state["conversation"] == ["remember this"]
        result = provider.exec(
            second, ["python", "-m", "unittest", "discover", "-s", "project", "-v"]
        )
        assert result.exit_code == 0, result.stderr
        assert (
            provider.exec(second, ["cat", "project/ignored.txt"]).stdout
            == "keep ignored data"
        )
        assert (
            provider.exec(second, ["cat", "project/notes.txt"]).stdout
            == "keep untracked data"
        )
        assert (
            provider.exec(
                second, ["test", "-f", "/runtime/native/codex/auth.json"]
            ).exit_code
            != 0
        )
        assert (
            "M app.py"
            in provider.exec(
                second, ["git", "-C", "project", "status", "--short"]
            ).stdout
        )
        provider.destroy(second)
        # Artifacts remain retrievable from the checkpoint after all compute is gone.
        store.restore(reference, Path(directory) / "offline")
        assert (
            Path(directory) / "offline/workspace/project/artifact.txt"
        ).read_text() == "test report"
        print(
            "Cloned, edited and tested a repository; destroyed compute; restored files and native state; reran tests."
        )
finally:
    provider.destroy(first)
    if second is not None:
        provider.destroy(second)

"""Real Linux hosted transport semantics through a local Docker test bridge."""

import json
import os
from dataclasses import replace
from uuid import uuid4

import pytest
import pytest_asyncio

from agno.sandbox.allocation import PostgresAllocationJournal
from agno.sandbox.base import ExecResult, SandboxError, SandboxSpec
from agno.sandbox.checkpoint import FileCheckpointStore
from agno.sandbox.client import SandboxRuntimeClient
from agno.sandbox.docker import DockerSandboxProvider
from agno.sandbox.hosted import HostedComputer, HostedSandboxProvider
from agno.sandbox.hosted_transfer import HostedCheckpointTransfer
from tests.integration.sandbox.test_postgres import URL
from tests.integration.sandbox.test_postgres import store as _store_fixture

store = _store_fixture
IMAGE = os.environ.get("AGNO_TEST_HOSTED_IMAGE")
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not URL or not IMAGE, reason="Set hosted image and sandbox Postgres URL"),
]


class LocalHosted(HostedSandboxProvider):
    backend = "local-test"

    def __init__(self, namespace, journal):
        super().__init__(namespace, journal)
        self.docker = DockerSandboxProvider(namespace)

    async def _create(self, spec, metadata):
        args = [
            "container",
            "run",
            "-d",
            "--user",
            "0:0",
            "--network",
            "none",
            "--memory",
            "512m",
            "--pids-limit",
            "256",
        ]
        for key, value in metadata.items():
            args.extend(["--label", key + "=" + value])
        for key, value in spec.env.items():
            args.extend(["--env", key + "=" + value])
        code, out, err = await self.docker._docker(*args, spec.image)
        assert code == 0, err
        return await self._get(out.decode().strip())

    async def _get(self, provider_ref):
        code, out, err = await self.docker._docker("container", "inspect", provider_ref)
        if code:
            if b"No such" in err:
                return None
            raise SandboxError(err.decode())
        record = json.loads(out)[0]
        return HostedComputer(record["Id"], record["Config"]["Labels"], record["State"]["Status"])

    async def _inventory(self, token):
        code, out, err = await self.docker._docker("container", "ls", "-aq", "--filter", "label=token=" + token)
        assert code == 0, err
        return [await self._get(ref) for ref in out.decode().splitlines()]

    async def _delete(self, provider_ref):
        code, _, err = await self.docker._docker("container", "rm", "-f", provider_ref)
        assert code == 0, err

    async def _command(self, provider_ref, argv, *, timeout):
        code, out, err = await self.docker._docker(
            "container", "exec", "--user", "0:0", provider_ref, *argv, timeout=timeout
        )
        return ExecResult(code, out.decode(), err.decode())

    async def _write(self, provider_ref, path, payload):
        code, _, err = await self.docker._docker(
            "container",
            "exec",
            "-i",
            "--user",
            "0:0",
            provider_ref,
            "python",
            "-I",
            "-c",
            "import sys; from pathlib import Path; Path(sys.argv[1]).write_bytes(sys.stdin.buffer.read())",
            path,
            input_data=payload,
        )
        assert code == 0, err

    async def _read(self, provider_ref, path, *, max_bytes):
        code, out, err = await self.docker._docker(
            "container",
            "exec",
            "--user",
            "0:0",
            provider_ref,
            "python",
            "-I",
            "-c",
            "import sys; from pathlib import Path; p=Path(sys.argv[1]); assert p.stat().st_size <= int(sys.argv[2]); sys.stdout.buffer.write(p.read_bytes())",
            path,
            str(max_bytes),
        )
        assert code == 0, err
        return out


@pytest_asyncio.fixture
async def hosted(store, tmp_path):
    journal = PostgresAllocationJournal(store, table_name=store.bindings.name + "_alloc")
    await journal.asetup()
    provider = LocalHosted(uuid4().hex, journal)
    spec = SandboxSpec("a", "s", 1, IMAGE, pids_limit=None, workspace_mb=None, env={"AGNO_SANDBOX_TEST_RUNTIME": "1"})
    handles = []

    async def create(generation=1):
        handle = await provider.acreate(replace(spec, generation=generation))
        handles.append(handle)
        return handle

    try:
        yield provider, create, HostedCheckpointTransfer(provider, FileCheckpointStore(tmp_path / "objects"))
    finally:
        for handle in handles:
            await provider.adestroy(handle)
        await store._transaction(lambda connection: journal.table.drop(connection))


async def test_commands_are_unprivileged_and_control_files_inaccessible(hosted):
    provider, create, _ = hosted
    handle = await create()
    result = await provider.aexec(
        handle,
        [
            "python",
            "-c",
            "import os; from pathlib import Path; print(os.getuid(), os.getgid()); print(next(l for l in Path('/proc/self/status').read_text().splitlines() if l.startswith('NoNewPrivs:'))); assert not os.access('/var/lib/agno-control', os.R_OK); assert not os.access('/usr/local/lib/python3.12/site-packages/agno', os.W_OK)",
        ],
    )
    assert result.exit_code == 0 and "1000 1000" in result.stdout and "NoNewPrivs:\t1" in result.stdout


async def test_runtime_and_frozen_checkpoint_restore_into_replacement(hosted):
    provider, create, transfer = hosted
    first = await create()
    client = SandboxRuntimeClient(provider)
    execution = await client.astart(first, execution_id="e", run_id="r", sdk="fixture", input="hello")
    pages = [page async for page in client.apages(execution, timeout=20)]
    assert pages[-1].result["type"] == "execution_finished"
    writer = "import time; from pathlib import Path\np=Path('/workspace/ticks')\nwhile True:\n p.write_text(str(time.monotonic())); time.sleep(.01)"
    result = await provider.aexec(
        first,
        [
            "python",
            "-c",
            "import subprocess; from pathlib import Path; Path('/runtime/native/native.txt').write_text('native'); Path('/workspace/link').symlink_to('fixture-effects.txt'); subprocess.Popen(['python','-c',"
            + repr(writer)
            + "], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)",
        ],
    )
    assert result.exit_code == 0
    reference = await transfer.acapture(first, state={"turn": 1})
    result = await provider._command(
        first.provider_ref,
        [
            "python",
            "-I",
            "-c",
            "import time; from pathlib import Path; p=Path('/workspace/ticks'); a=p.read_bytes(); time.sleep(.1); assert a == p.read_bytes()",
        ],
        timeout=5,
    )
    assert result.exit_code == 0, result.stderr
    with pytest.raises(SandboxError, match="Captured compute"):
        await provider.aexec(first, ["true"])
    second = await create(2)
    assert await transfer.arestore(second, reference) == {"turn": 1}
    restored = await provider.aexec(
        second,
        [
            "python",
            "-c",
            "from pathlib import Path; assert Path('link').read_text() == 'r\\n'; assert Path('/runtime/native/native.txt').read_text() == 'native'; assert Path('ticks').exists(); print('restored')",
        ],
    )
    assert restored.exit_code == 0 and restored.stdout == "restored\n"


async def test_restore_rejects_used_computer_and_stops_it(hosted):
    provider, create, transfer = hosted
    source = await create()
    reference = await transfer.acapture(source, state={})
    target = await create(2)
    assert (await provider.aexec(target, ["true"])).exit_code == 0
    with pytest.raises(SandboxError, match="unused"):
        await transfer.arestore(target, reference)
    assert await provider._get(target.provider_ref) is None


async def test_vercel_staging_bridge_rejects_tampering_and_preserves_root_ownership(hosted):
    import hashlib

    from agno.sandbox.vercel import _EXPORT, _IMPORT

    provider, create, _ = hosted
    handle = await create()
    payload = b"exact bytes from service"
    staging = "/tmp/upload"
    target = "/var/lib/agno-control/" + uuid4().hex + ".json"
    await provider._write(handle.provider_ref, staging, b"tampered")
    args = ["python", "-I", "-c", _IMPORT, staging, target, str(len(payload)), hashlib.sha256(payload).hexdigest()]
    bad = await provider._command(handle.provider_ref, args, timeout=5)
    assert bad.exit_code != 0 and "digest mismatch" in bad.stderr
    await provider._write(handle.provider_ref, staging, payload)
    good = await provider._command(handle.provider_ref, args, timeout=5)
    assert good.exit_code == 0, good.stderr
    verify = await provider._command(
        handle.provider_ref,
        [
            "python",
            "-I",
            "-c",
            "import os,stat,sys; s=os.stat(sys.argv[1]); assert s.st_uid == 0 and stat.S_IMODE(s.st_mode) == 0o600",
            target,
        ],
        timeout=5,
    )
    assert verify.exit_code == 0, verify.stderr
    export = await provider._command(
        handle.provider_ref, ["python", "-I", "-c", _EXPORT, target, "/tmp/download", str(len(payload))], timeout=5
    )
    assert export.exit_code == 0, export.stderr
    assert await provider._read(handle.provider_ref, "/tmp/download", max_bytes=len(payload)) == payload


async def test_vercel_staging_bridge_rejects_source_symlinks(hosted):
    import hashlib

    from agno.sandbox.vercel import _IMPORT

    provider, create, _ = hosted
    handle = await create()
    await provider.aexec(handle, ["ln", "-s", "/etc/passwd", "/tmp/upload-link"])
    result = await provider._command(
        handle.provider_ref,
        [
            "python",
            "-I",
            "-c",
            _IMPORT,
            "/tmp/upload-link",
            "/var/lib/agno-control/target",
            "1",
            hashlib.sha256(b"x").hexdigest(),
        ],
        timeout=5,
    )
    assert result.exit_code != 0 and "Too many levels" in result.stderr


async def test_capture_waits_for_control_request_crossing_privilege_boundary(hosted):
    import asyncio

    provider, create, transfer = hosted
    handle = await create()
    # Hold a real root helper immediately before privilege drop. Capture must
    # wait for this accepted control request, not miss it in the UID scan.
    script = """import time
from pathlib import Path
from agno.sandbox import hosted_runtime as runtime
original=runtime._user_process
def delayed(operation, request):
 Path('/tmp/before-drop').touch()
 time.sleep(2)
 return original(operation, request)
runtime._user_process=delayed
runtime._control()
result=runtime._dispatch('exec', {'argv':['python','-c',"from pathlib import Path; Path('after-drop').write_text('finished')"], 'timeout':5, 'max_output_bytes':1024})
assert result['exit_code']==0
"""
    task = asyncio.create_task(provider._command(handle.provider_ref, ["python", "-I", "-c", script], timeout=10))
    try:
        for _ in range(30):
            result = await provider._command(handle.provider_ref, ["test", "-f", "/tmp/before-drop"], timeout=5)
            if result.exit_code == 0:
                break
            await asyncio.sleep(0.02)
        else:
            pytest.fail("Root helper did not reach the privilege boundary")
        reference = await transfer.acapture(handle, state={})
        result = await task
        assert result.exit_code == 0, result.stderr
        restored = transfer.store.root.parent / "race-restore"
        await transfer.archive.arestore(await transfer.store.averify(reference), restored)
        assert (restored / "workspace" / "after-drop").read_text() == "finished"
    finally:
        if not task.done():
            await provider.adestroy(handle)
        await asyncio.gather(task, return_exceptions=True)


async def test_initialized_image_marker_is_bound_to_exact_allocation(hosted):
    provider, create, _ = hosted
    handle = await create()
    assert await provider._control(handle, "init", {}) == {"initialized": True}
    wrong = await provider._command(
        handle.provider_ref, ["python", "-I", "-m", "agno.sandbox.hosted_runtime", "init", "a" * 64], timeout=5
    )
    assert wrong.exit_code != 0 and "another allocation" in wrong.stderr
    assert (await provider.aexec(handle, ["true"])).exit_code == 0

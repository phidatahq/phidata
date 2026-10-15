"""Attachments on a ``sandbox=`` agent: the canonical wire the queue stores, and what the coordinator receives.

The harness is the single validation point for Python callers, HTTP and the queue worker, so these tests drive
``_harness.submission`` / ``_execution`` and the public ``arun`` with only the coordinator replaced by a recorder.
"""

import json

import pytest

from agno.agents.claude import ClaudeAgent
from agno.agents.codex import CodexAgent
from agno.exceptions import UnsupportedMediaError
from agno.media import Audio, File, Image
from agno.sandbox import _harness
from agno.sandbox.docker import DockerSandbox
from agno.sandbox.fixture import FixtureAgent
from agno.sandbox.media import MAX_MEDIA_BYTES, decode_media, encode_media

SANDBOX_ENV = {"AGNO_SANDBOX_TEST_RUNTIME": "1"}


def _agent(cls=FixtureAgent):
    return cls(sandbox=DockerSandbox("img:none", env=SANDBOX_ENV))


def _media():
    return dict(images=[Image(content=b"png", format="png")], files=[File(content=b"abc", filename="a.txt")])


def test_python_media_becomes_the_canonical_json_wire_in_the_run_options():
    agent = _agent()
    options = _harness.submission(agent, "hello", agent._media_kwargs(**_media()))
    assert options["sandbox_media"] == encode_media(**_media())
    assert json.loads(json.dumps(options)) == options


@pytest.mark.parametrize("cls", [FixtureAgent, ClaudeAgent, CodexAgent])
def test_every_sandboxable_harness_accepts_images_and_files_and_refuses_the_rest(cls):
    agent = _agent(cls)
    assert "sandbox_media" in _harness.submission(agent, "hello", agent._media_kwargs(**_media()))
    with pytest.raises(UnsupportedMediaError):
        agent._media_kwargs(audio=[Audio(content=b"audio")])


def test_queue_wire_is_accepted_and_revalidated_when_the_worker_replays_it():
    agent = _agent()
    wire = encode_media(**_media())
    assert _harness.submission(agent, "hello", {"sandbox_media": wire})["sandbox_media"] == wire
    with pytest.raises(ValueError):
        _harness.submission(agent, "hello", {"sandbox_media": [{**wire[0], "name": "../escape"}]})
    with pytest.raises(ValueError, match="either"):
        _harness.submission(agent, "hello", {"sandbox_media": wire, "media": _media()})


def test_the_whole_runtime_request_limit_counts_the_attachments():
    agent = _agent()
    full = {"files": [File(content=b"a" * MAX_MEDIA_BYTES, filename="full.bin")]}
    _harness.submission(agent, "x", {"media": full})
    with pytest.raises(ValueError, match="exceeds"):
        _harness.submission(agent, "x" * 400_000, {"media": full})


def test_a_local_file_is_read_at_submission_and_survives_removal_of_its_source(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_bytes(b"local bytes")
    agent = _agent()
    options = _harness.submission(agent, "hello", {"media": {"files": [File(filepath=path)]}})
    path.unlink()
    (file,) = decode_media(options["sandbox_media"])["files"]
    assert file.content == b"local bytes" and file.filename == "notes.txt"
    assert str(tmp_path) not in json.dumps(options)


def test_the_coordinator_is_called_with_decoded_attachments_and_text_only_calls_are_unchanged():
    agent = _agent()
    wire = encode_media(**_media())
    execution = _harness._execution(agent, "hello", {"sandbox_media": wire, "run_id": "r"})
    assert [image.content for image in execution["images"]] == [b"png"]
    assert [file.content for file in execution["files"]] == [b"abc"]
    text_only = _harness._execution(agent, "hello", {"run_id": "r"})
    assert "images" not in text_only and "files" not in text_only


class _Recorder:
    def __init__(self):
        self.calls = []

    async def arun(self, session_id, **execution):
        from agno.run.agent import RunOutput
        from agno.run.base import RunStatus

        self.calls.append(execution)
        return RunOutput(run_id=execution["run_id"], session_id=session_id, status=RunStatus.completed, content="ok")

    async def astream(self, session_id, **execution):
        self.calls.append(execution)
        if False:
            yield None


@pytest.mark.asyncio
@pytest.mark.parametrize("stream", [False, True])
async def test_public_arun_forwards_attachments_to_the_coordinator(monkeypatch, stream):
    agent, recorder = _agent(), _Recorder()
    monkeypatch.setattr(_harness, "coordinator", lambda _: recorder)
    if stream:
        async for _ in agent.arun("hello", stream=True, session_id="s", run_id="r", **_media()):
            pass
    else:
        await agent.arun("hello", session_id="s", run_id="r", **_media())
    (execution,) = recorder.calls
    assert [image.content for image in execution["images"]] == [b"png"]
    assert [file.filename for file in execution["files"]] == ["a.txt"]


@pytest.mark.asyncio
async def test_invalid_attachments_fail_before_the_coordinator_is_reached(monkeypatch):
    agent, recorder = _agent(), _Recorder()
    monkeypatch.setattr(_harness, "coordinator", lambda _: recorder)
    with pytest.raises(ValueError):
        await agent.arun("hello", session_id="s", run_id="r", files=[File(url="https://example.com/a.txt")])
    assert recorder.calls == []


# --- the pending run row ---------------------------------------------------------------------------------------
# The store refuses to claim a run whose input differs from the row accepted for it, so the pending row has to carry
# exactly the attachments the coordinator will write when the run starts. They come from the ticket, which already
# holds the canonical wire; the hook itself is only given the run id and the text.


class _Store:
    def __init__(self, payload):
        self.prepared = []
        self.job = {"id": "r", "payload": payload}

    async def get_job(self, run_id):
        return self.job if run_id == "r" else None

    async def aprepare(self, run):
        self.prepared.append(run)


@pytest.mark.asyncio
@pytest.mark.parametrize("with_media", [True, False])
async def test_the_pending_row_carries_the_same_input_the_coordinator_writes_at_claim(monkeypatch, with_media):
    from types import SimpleNamespace

    from agno.run.agent import RunInput

    agent = _agent()
    wire = encode_media(images=[Image(content=b"png", format="png")], files=[File(content=b"abc", filename="a.txt")])
    store = _Store({"input": "hello", "kwargs": {"sandbox_media": wire} if with_media else {}})
    monkeypatch.setattr("agno.os.job_queue.get_active_queue_worker", lambda: SimpleNamespace(store=store))
    monkeypatch.setattr(_harness, "coordinator", lambda _: SimpleNamespace(store=store))
    pending = await _harness.aprepare_pending_run(agent, "r", "s", None, "hello")
    claimed = RunInput(input_content="hello", **decode_media(wire if with_media else []))
    assert pending.input.to_dict() == claimed.to_dict()
    assert store.prepared[0]["input"] == claimed.to_dict()
    assert bool(pending.input.files) is with_media


@pytest.mark.parametrize("stream", [False, True])
def test_the_synchronous_public_run_forwards_attachments_too(monkeypatch, stream):
    agent, recorder = _agent(), _Recorder()
    monkeypatch.setattr(_harness, "coordinator", lambda _: recorder)
    result = agent.run("hello", stream=stream, session_id="s", run_id="r", **_media())
    if stream:
        list(result)
    (execution,) = recorder.calls
    assert [file.content for file in execution["files"]] == [b"abc"]

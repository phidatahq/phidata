"""The body of a run submission to a sandboxed agent is bounded by the bytes actually received, before it is parsed.

Framework form parsing spools every uploaded file to disk and reads the whole body before an attachment limit can
reject it. These tests drive the ASGI middleware directly with chunked bodies that are never held in memory.
"""

import json

import pytest

from agno.os.middleware.sandbox_body_limit import MAX_SANDBOX_REQUEST_BODY, SandboxRunBodyLimit

CHUNK = 64 * 1024
LIMIT = 8 * CHUNK


class Downstream:
    """An app that reads its whole request body, as the framework's form parser does."""

    def __init__(self, status=200):
        self.status, self.called, self.body_seen, self.disconnected = status, 0, 0, False

    async def __call__(self, scope, receive, send):
        self.called += 1
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                self.disconnected = True
                break
            self.body_seen += len(message.get("body", b""))
            if not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": self.status, "headers": []})
        await send({"type": "http.response.body", "body": b"downstream"})


async def call(app, *, chunks, path="/agents/coder/runs", method="POST", headers=None):
    """Run the app with a body of ``chunks`` chunks, counting what the client was asked for."""
    pulled = 0
    sent = []

    async def receive():
        nonlocal pulled
        if pulled >= chunks:
            return {"type": "http.disconnect"}
        pulled += 1
        return {"type": "http.request", "body": b"x" * CHUNK, "more_body": pulled < chunks}

    async def send(message):
        sent.append(message)

    scope = {"type": "http", "method": method, "path": path, "headers": headers or []}
    await app(scope, receive, send)
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return status, body, pulled


def limited(downstream, ids=("coder",), limit=LIMIT):
    return SandboxRunBodyLimit(downstream, agent_ids=set(ids), max_bytes=limit)


@pytest.mark.asyncio
async def test_a_body_within_the_limit_reaches_the_app_untouched():
    downstream = Downstream()
    status, body, _ = await call(limited(downstream), chunks=LIMIT // CHUNK)
    assert (status, body) == (200, b"downstream") and downstream.body_seen == LIMIT


@pytest.mark.asyncio
async def test_a_body_over_the_limit_is_refused_after_reading_only_a_little_more_than_the_limit():
    downstream = Downstream()
    status, body, pulled = await call(limited(downstream), chunks=10_000)  # 640 MiB if it were all read
    assert status == 413 and "limit" in json.loads(body)["detail"]
    assert pulled * CHUNK <= LIMIT + CHUNK
    assert downstream.body_seen <= LIMIT and downstream.disconnected


@pytest.mark.asyncio
async def test_a_content_length_over_the_limit_is_refused_without_reading_the_body():
    downstream = Downstream()
    status, _, pulled = await call(
        limited(downstream), chunks=10_000, headers=[(b"content-length", str(LIMIT + 1).encode())]
    )
    assert status == 413 and pulled == 0 and downstream.called == 0


@pytest.mark.asyncio
async def test_a_content_length_that_understates_the_body_does_not_bypass_the_limit():
    downstream = Downstream()
    status, _, pulled = await call(limited(downstream), chunks=10_000, headers=[(b"content-length", b"10")])
    assert status == 413 and pulled * CHUNK <= LIMIT + CHUNK


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,method",
    [
        ("/agents/someone-else/runs", "POST"),
        ("/agents/coder/runs/abc/cancel", "POST"),
        ("/agents/coder/runs", "GET"),
        ("/teams/coder/runs", "POST"),
    ],
)
async def test_other_agents_routes_and_methods_are_not_limited(path, method):
    downstream = Downstream()
    status, _, _ = await call(limited(downstream), chunks=3 * LIMIT // CHUNK, path=path, method=method)
    assert status == 200 and downstream.body_seen == 3 * LIMIT


@pytest.mark.asyncio
async def test_a_trailing_slash_or_prefix_is_still_the_run_route():
    for path in ("/agents/coder/runs/", "/os/agents/coder/runs"):
        status, _, _ = await call(limited(Downstream()), chunks=10_000, path=path)
        assert status == 413


@pytest.mark.asyncio
async def test_an_app_that_fails_while_the_body_is_cut_off_still_answers_413():
    class Failing(Downstream):
        async def __call__(self, scope, receive, send):
            await super().__call__(scope, receive, send)
            raise RuntimeError("the form parser gave up on a truncated body")

    status, _, _ = await call(limited(Failing(status=400)), chunks=10_000)
    assert status == 413


@pytest.mark.asyncio
async def test_a_failure_unrelated_to_the_limit_is_not_hidden():
    class Failing(Downstream):
        async def __call__(self, scope, receive, send):
            raise RuntimeError("unrelated")

    with pytest.raises(RuntimeError, match="unrelated"):
        await call(limited(Failing()), chunks=1)


def test_the_default_limit_covers_every_request_the_route_could_accept_before():
    # The runtime request (message + options + attachments, base64) is capped at 1 MiB; form encoding can at worst
    # triple the text of a urlencoded body. 4 MiB leaves headroom over that and over multipart framing.
    assert MAX_SANDBOX_REQUEST_BODY == 4 * 1024 * 1024
    assert MAX_SANDBOX_REQUEST_BODY >= 3 * 1024 * 1024 + 64 * 1024

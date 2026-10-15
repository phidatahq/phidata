"""Bound the body of run submissions to sandboxed agents by the bytes actually received."""

import re
from typing import Any, Collection, Optional

from starlette.responses import JSONResponse

# A transport limit of its own, not a bound the attachment limits imply: the route never limited the raw body. The
# largest request written the usual way (uploads, or JSON fields as json.dumps and a minimal url-encoder write them)
# that still fits the 1 MiB runtime request is about 3 MiB, and 4 MiB sits above that. A body padded with whitespace,
# \u escapes or percent-encoded bytes can carry the same attachments in more bytes, and is refused.
MAX_SANDBOX_REQUEST_BODY = 4 * 1024 * 1024

_RUN_ROUTE = re.compile(r"/agents/([^/]+)/runs/?$")


class SandboxRunBodyLimit:
    """Refuse an oversized run submission before the framework parses it.

    Form parsing reads the whole body, spooling every uploaded file to disk, before an attachment limit can reject
    it. This counts the body as it arrives, so it holds with a missing or understated Content-Length and with chunked
    transfer, and it stops delivering the body to the app once the limit is passed. It applies to POST
    ``/agents/{id}/runs`` for the given agent ids only.
    """

    def __init__(self, app: Any, *, agent_ids: Collection[str], max_bytes: int = MAX_SANDBOX_REQUEST_BODY) -> None:
        self.app = app
        self.agent_ids = frozenset(agent_ids)
        self.max_bytes = max_bytes

    def _applies(self, scope: Any) -> bool:
        if scope["type"] != "http" or scope["method"] != "POST":
            return False
        match = _RUN_ROUTE.search(scope["path"])
        return match is not None and match.group(1) in self.agent_ids

    @staticmethod
    def _declared(scope: Any) -> Optional[int]:
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    return int(value)
                except ValueError:
                    return None
        return None

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if not self._applies(scope):
            await self.app(scope, receive, send)
            return
        reject = JSONResponse(
            status_code=413,
            content={"detail": f"The request body exceeds the {self.max_bytes}-byte limit for sandboxed runs"},
        )
        declared = self._declared(scope)
        if declared is not None and declared > self.max_bytes:
            await reject(scope, receive, send)
            return

        received = 0
        exceeded = False
        started = False

        async def bounded_receive() -> Any:
            nonlocal received, exceeded
            if exceeded:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    exceeded = True
                    return {"type": "http.disconnect"}
            return message

        async def guarded_send(message: Any) -> None:
            nonlocal started
            if not exceeded:
                started = started or message["type"] == "http.response.start"
                await send(message)

        try:
            await self.app(scope, bounded_receive, guarded_send)
        except Exception:
            # The parser failing on the truncated body is the limit's doing, not a server error.
            if not exceeded:
                raise
        # An app that already began its response cannot be given a second one; the server ends that response early.
        if exceeded and not started:
            await reject(scope, receive, send)

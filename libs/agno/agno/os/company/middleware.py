"""Normalize authentication and routing errors without altering other AgentOS APIs."""

import json
import re
from typing import Any
from uuid import uuid4


class CompanyProtocolMiddleware:
    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http" or not scope["path"].startswith("/company/v1/"):
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        supplied = headers.get(b"x-request-id", b"").decode("latin1")
        rid = supplied if re.fullmatch(r"[A-Za-z0-9._:-]{1,200}", supplied) else str(uuid4())
        scope.setdefault("state", {})["company_request_id"] = rid
        start = None
        chunks = []

        async def wrapped(message: Any) -> None:
            nonlocal start
            if message["type"] == "http.response.start":
                start = message
                return
            if message["type"] != "http.response.body" or start is None:
                await send(message)
                return
            chunks.append(message.get("body", b""))
            if message.get("more_body"):
                return
            body = b"".join(chunks)
            status = start["status"]
            if status >= 400:
                try:
                    existing = json.loads(body)
                except (ValueError, UnicodeDecodeError):
                    existing = {}
                if "error" not in existing:
                    codes = {401: "unauthenticated", 403: "forbidden", 404: "not_found", 422: "validation_error"}
                    body = json.dumps(
                        {
                            "error": {
                                "code": codes.get(status, "request_failed"),
                                "message": "Company request could not be authorized or completed",
                                "details": {},
                            },
                            "request_id": rid,
                        }
                    ).encode()
            start["headers"] = [
                (key, value)
                for key, value in start.get("headers", [])
                if key.lower() not in (b"content-length", b"x-request-id", b"cache-control")
            ]
            start["headers"] += [
                (b"content-length", str(len(body)).encode()),
                (b"x-request-id", rid.encode()),
                (b"cache-control", b"no-store"),
            ]
            await send(start)
            await send({"type": "http.response.body", "body": body})

        await self.app(scope, receive, wrapped)

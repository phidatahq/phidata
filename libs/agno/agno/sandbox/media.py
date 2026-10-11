"""Bounded byte-only media transport; service filesystem paths never cross RPC."""

import base64
import hashlib
import os
import stat
from typing import Any, Dict, List

from agno.agents._media import _mime_for, _name_for
from agno.exceptions import UnsupportedMediaError
from agno.media import File, Image

MAX_MEDIA_BYTES = 512 * 1024
MAX_MEDIA_ITEMS = 16


def encode_media(media: Dict[str, Any], *, allow_local_paths: bool = False) -> List[Dict[str, Any]]:
    unsupported = [key for key, values in media.items() if values and key not in ("images", "files")]
    if unsupported:
        raise UnsupportedMediaError("Sandbox inputs support images and files only", media=unsupported)
    result: List[Dict[str, Any]] = []
    total = 0
    content: Any
    for group, kind, cls in (("images", "image", Image), ("files", "file", File)):
        for index, item in enumerate(media.get(group) or []):
            if len(result) >= MAX_MEDIA_ITEMS:
                raise ValueError("Sandbox input accepts at most 16 attachments")
            if isinstance(item, dict):
                if item.get("filepath") or item.get("url") or item.get("media_reference") or item.get("external"):
                    raise ValueError(
                        "HTTP sandbox attachments require inline bytes, not filesystem paths or remote references"
                    )
                raw = item.get("content")
                if not isinstance(raw, str) or len(raw) > (MAX_MEDIA_BYTES * 4 // 3 + 4):
                    raise ValueError("JSON attachment content must be bounded base64")
                try:
                    content = base64.b64decode(raw, validate=True)
                except ValueError as error:
                    raise ValueError("JSON attachment content must be base64") from error
                item = cls(
                    **{key: item[key] for key in ("format", "mime_type", "filename", "name") if key in item},
                    content=content,
                    id="inline",
                )
            if not isinstance(item, cls) or item.url or item.media_reference or getattr(item, "external", None):
                raise ValueError("Sandbox attachments require inline bytes or explicit SDK local files")
            if item.filepath:
                if not allow_local_paths:
                    raise ValueError("HTTP sandbox attachments cannot read service filesystem paths")
                fd = os.open(item.filepath, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                with os.fdopen(fd, "rb") as stream:
                    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                        raise ValueError("Sandbox SDK attachments must be regular files")
                    if os.fstat(stream.fileno()).st_size > MAX_MEDIA_BYTES - total:
                        raise ValueError("Sandbox attachments exceed 512 KiB total")
                    content = stream.read(MAX_MEDIA_BYTES - total + 1)
            else:
                content = item.content
                if isinstance(content, str) and kind == "file":
                    content = content.encode()
                if not isinstance(content, bytes):
                    raise ValueError("Sandbox attachment content must be bytes")
            total += len(content)
            if total > MAX_MEDIA_BYTES:
                raise ValueError("Sandbox attachments exceed 512 KiB total")
            value = {"kind": kind, "content": base64.b64encode(content).decode(), "name": _name_for(item, kind, index)}
            mime = _mime_for(item)
            if mime is not None:
                value["mime_type"] = mime
            if item.format is not None:
                value["format"] = str(item.format)
            result.append(value)
    validate_media(result)
    return result


def validate_media(value: Any) -> None:
    if not isinstance(value, list) or len(value) > MAX_MEDIA_ITEMS:
        raise ValueError("Sandbox media must be a list with at most 16 items")
    total = 0
    for item in value:
        if not isinstance(item, dict) or set(item) - {"kind", "content", "name", "mime_type", "format"}:
            raise ValueError("Unsupported sandbox attachment fields")
        if item.get("kind") not in ("image", "file"):
            raise ValueError("Unsupported sandbox attachment kind")
        name = item.get("name")
        if (
            not isinstance(name, str)
            or not name
            or len(name) > 120
            or any(char in name for char in ("/", "\\", "\x00"))
            or name in (".", "..")
        ):
            raise ValueError("Attachment name must be a bounded filename")
        for key in ("mime_type", "format"):
            if key in item and (not isinstance(item[key], str) or len(item[key]) > 128):
                raise ValueError("Attachment media metadata must be bounded strings")
        raw = item.get("content")
        if not isinstance(raw, str) or len(raw) > MAX_MEDIA_BYTES * 4 // 3 + 4:
            raise ValueError("Sandbox media content must be bounded base64")
        try:
            content = base64.b64decode(raw, validate=True)
        except ValueError as error:
            raise ValueError("Sandbox media content must be base64") from error
        if base64.b64encode(content).decode() != raw:
            raise ValueError("Sandbox media base64 must be canonical")
        total += len(content)
    if total > MAX_MEDIA_BYTES:
        raise ValueError("Sandbox attachments exceed 512 KiB total")


def decode_media(value: Any) -> Dict[str, Any]:
    validate_media(value)
    result: Dict[str, Any] = {}
    for index, item in enumerate(value):
        content = base64.b64decode(item["content"], validate=True)
        # Stable IDs keep idempotent submissions and persisted inputs identical
        # when another replica reconstructs the same queued attachment bytes.
        identity = hashlib.sha256((item["kind"] + ":" + str(index) + ":" + item["name"]).encode() + content).hexdigest()
        fields = {key: item[key] for key in ("mime_type", "format") if key in item}
        if item["kind"] == "image":
            result.setdefault("images", []).append(Image(content=content, id=identity, **fields))
        else:
            result.setdefault("files", []).append(File(content=content, filename=item["name"], id=identity, **fields))
    return result

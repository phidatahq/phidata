"""Utility functions for the Google ADK adapter."""

import mimetypes
from typing import Any, Dict, List, Optional

_DEFAULT_MIME = {
    "images": "image/png",
    "audio": "audio/wav",
    "videos": "video/mp4",
    "files": "application/octet-stream",
}

# URI schemes Gemini can read directly; anything else is downloaded and sent inline.
_NATIVE_URI_PREFIXES = ("gs://", "https://generativelanguage.googleapis.com/")


def _mime_for(item: Any, kind: str) -> str:
    mime = getattr(item, "mime_type", None)
    if mime:
        return str(mime)
    fmt = getattr(item, "format", None)
    if fmt:
        guessed, _ = mimetypes.guess_type(f"file.{str(fmt).lower().lstrip('.')}")
        if guessed:
            return guessed
    for attr in ("filepath", "filename", "url"):
        name = getattr(item, attr, None)
        if name:
            guessed, _ = mimetypes.guess_type(str(name))
            if guessed:
                return guessed
    return _DEFAULT_MIME[kind]


async def abuild_media_parts(media: Optional[Dict[str, List[Any]]]) -> List[Any]:
    """Convert Agno media objects into Gemini parts for the ADK user message.

    Bytes and local files go inline. Google-hosted URIs (Cloud Storage, the Gemini Files
    API) are referenced by URI; other URLs are downloaded and sent inline too, since the
    Gemini API does not fetch arbitrary web URLs. Downloads and file reads are awaited so
    they do not block the event loop serving other runs.
    """
    from google.genai import types

    parts: List[Any] = []
    for kind, items in (media or {}).items():
        for item in items or []:
            mime = _mime_for(item, kind)
            url = getattr(item, "url", None)
            if url and not getattr(item, "content", None) and str(url).startswith(_NATIVE_URI_PREFIXES):
                parts.append(types.Part.from_uri(file_uri=str(url), mime_type=mime))
                continue
            data = await item.aget_content_bytes()
            if not data:
                raise ValueError(f"Could not read the {kind[:-1] if kind != 'audio' else 'audio'} input {item!r}")
            parts.append(types.Part.from_bytes(data=data, mime_type=mime))
    return parts

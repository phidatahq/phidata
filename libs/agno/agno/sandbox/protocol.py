"""Pure request validation shared by the control plane and Linux runtime."""

import json
import math
import os
from typing import Any, Dict

_VERSION = 1
_MAX_REQUEST = 1024 * 1024


def validate_request(request: Dict[str, Any]) -> None:
    if type(request.get("version")) is not int or request["version"] != _VERSION:
        raise ValueError("Unsupported runtime protocol version")
    for key in ("execution_id", "run_id", "session_id", "agent_id"):
        if not isinstance(request.get(key), str) or not request[key] or len(request[key]) > 256:
            raise ValueError("Runtime requires bounded string identities")
    if request.get("sdk") not in ("claude", "codex", "fixture"):
        raise ValueError("Unsupported runtime SDK")
    if not isinstance(request.get("input"), str) or not isinstance(request.get("config", {}), dict):
        raise ValueError("Runtime input must be text and configuration must be JSON")
    if request["sdk"] == "fixture" and os.environ.get("AGNO_SANDBOX_TEST_RUNTIME") != "1":
        raise ValueError("The fixture runtime is disabled")
    if {
        "db",
        "cwd",
        "id",
        "retries",
        "env",
        "client_options",
        "options",
        "options_kwargs",
        "thread_kwargs",
        "keep_uploads",
    } & set(request.get("config", {})):
        raise ValueError("Runtime owns database, workspace, identity, process environment and retry configuration")
    from agno.sandbox.media import validate_media

    validate_media(request.get("media", []))
    timeout = request.get("execution_timeout", 900)
    if not isinstance(timeout, (float, int)) or not math.isfinite(timeout) or not 0 < timeout <= 86400:
        raise ValueError("Runtime execution timeout must be between 0 and 86400 seconds")
    if len(json.dumps(request, allow_nan=False, separators=(",", ":")).encode()) > _MAX_REQUEST:
        raise ValueError("Runtime request exceeds its limit")

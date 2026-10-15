"""Prepare a pinned repository inside the sandbox before starting the model."""

import asyncio
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict


def validate_repository(value: Any) -> Dict[str, str]:
    """Validate the initial GitHub repository contract without making network calls."""
    if not isinstance(value, dict) or set(value) != {"url", "commit"}:
        raise ValueError("repository requires exactly url and commit")
    if (
        not isinstance(value["url"], str)
        or not re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value["url"])
        or any(part in (".", "..") for part in value["url"].split("/")[-2:])
    ):
        raise ValueError("repository.url must be a GitHub HTTPS repository without credentials")
    if not isinstance(value["commit"], str) or not re.fullmatch(r"[0-9a-f]{40}", value["commit"]):
        raise ValueError("repository.commit must be a full commit SHA")
    return dict(value)


def _prepare(repository: Dict[str, str], workspace: Path, native: Path, *, resume: bool) -> Path:
    repository = validate_repository(repository)
    target = workspace / "repository"
    marker = native / "repository.json"
    if marker.exists():
        if json.loads(marker.read_text()) != repository or not (target / ".git").is_dir():
            raise ValueError("Restored repository does not match the pinned source")
        # Preserve the engineer's commits and uncommitted files on subsequent turns.
        return target
    if resume or target.exists():
        raise ValueError("Repository checkpoint is missing its source identity")
    staging = workspace / ".repository-prepare"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    # Credentials belong to the sandbox configuration, never the request or remote URL.
    token = env.get("GITHUB_TOKEN")
    if token:
        import base64

        env["GIT_CONFIG_COUNT"] = "1"
        env["GIT_CONFIG_KEY_0"] = "http.https://github.com/.extraheader"
        encoded = base64.b64encode(("x-access-token:" + token).encode()).decode()
        env["GIT_CONFIG_VALUE_0"] = "Authorization: Basic " + encoded

    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", "-c", "http.followRedirects=false", *args],
            cwd=staging,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode:
            # Git errors may contain credential material from operator configuration.
            raise RuntimeError("Repository preparation failed; check repository access and the pinned commit")
        return result.stdout.strip()

    try:
        git("init", "--quiet")
        git("remote", "add", "origin", repository["url"])
        git("fetch", "--depth=1", "origin", repository["commit"])
        git("checkout", "--detach", repository["commit"])
        if git("rev-parse", "HEAD") != repository["commit"]:
            raise ValueError("Repository checkout does not match the pinned commit")
        staging.rename(target)
        native.mkdir(parents=True, exist_ok=True)
        temporary = marker.with_suffix(".tmp")
        temporary.write_text(json.dumps(repository, sort_keys=True))
        temporary.replace(marker)
        return target
    finally:
        if staging.exists():
            shutil.rmtree(staging)


async def _aprepare(repository: Dict[str, str], workspace: Path, native: Path, *, resume: bool) -> Path:
    return await asyncio.to_thread(_prepare, repository, workspace, native, resume=resume)

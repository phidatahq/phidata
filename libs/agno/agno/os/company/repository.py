"""Resolve an approved Product branch to immutable execution source."""

import re
from typing import Any, Dict, Optional
from urllib.parse import quote

import httpx

from agno.os.company.policy import CompanyError


def _resolve_commit(repository: Dict[str, Any], token: Optional[str]) -> Dict[str, str]:
    slug = repository["url"].removeprefix("https://github.com/").removesuffix(".git")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        with httpx.Client(timeout=10, follow_redirects=False, trust_env=False) as client:
            response = client.get(
                "https://api.github.com/repos/" + slug + "/commits/" + quote(repository["branch"], safe=""),
                headers=headers,
            )
            response.raise_for_status()
            sha = response.json()["sha"]
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise ValueError("Invalid commit")
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise CompanyError(
            409,
            "source_unavailable",
            "Cannot resolve the Product branch; check repository access before accepting Ready",
        ) from exc
    return {"url": repository["url"], "commit": sha}

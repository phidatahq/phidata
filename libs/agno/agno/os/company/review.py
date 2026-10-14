"""Read-only verification of an exact GitHub pull request revision."""

from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from agno.os.company.policy import CompanyError
from agno.os.company.schemas import PullRequestReview


async def _verify_merge(
    review: Dict[str, Any], since: datetime, token: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    link = PullRequestReview.model_validate(review)
    owner, repo, _, number = link.url.removeprefix("https://github.com/").split("/")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2026-03-10"}
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            response = await client.get(f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}", headers=headers)
            response.raise_for_status()
            data = response.json()
        if (
            data["number"] != int(number)
            or data["base"]["repo"]["full_name"].lower() != f"{owner}/{repo}".lower()
            or data["html_url"].lower() != link.url.lower()
        ):
            raise CompanyError(409, "pull_request_changed", "GitHub returned a different pull request")
        if data["head"]["sha"] != link.head_sha:
            raise CompanyError(
                409, "revision_changed", "The pull request revision changed; a human must link the new revision"
            )
        if data.get("merged") is not True:
            if data.get("state") == "closed":
                raise CompanyError(409, "not_merged", "The pull request was closed without merging")
            return None
        actor = data["merged_by"]
        if actor["type"] != "User" or not actor["login"] or not actor["id"] or actor["login"].endswith("[bot]"):
            raise CompanyError(409, "human_merge_required", "The pull request must be merged by a GitHub user account")
        merged_at = datetime.fromisoformat(data["merged_at"].replace("Z", "+00:00"))
        if merged_at.tzinfo is None or merged_at < since:
            raise CompanyError(409, "stale_merge", "The merge predates this Task review")
        return {
            "url": link.url,
            "head_sha": link.head_sha,
            "merged_at": data["merged_at"],
            "merge_commit_sha": data.get("merge_commit_sha"),
            "merged_by": {"id": actor["id"], "login": actor["login"]},
        }
    except (httpx.HTTPError, KeyError, TypeError, ValueError, AttributeError) as exc:
        # Never surface response bodies, credentials or transport details to Task readers.
        raise CompanyError(
            503, "merge_verification_unavailable", "Could not verify the pull request with GitHub; it remains In review"
        ) from exc

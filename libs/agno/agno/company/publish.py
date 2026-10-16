"""Publish stored Task patches on the host and verify exact-head merges."""

import asyncio
import hashlib
import inspect
import json
import logging
import os
import re
import tempfile
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from agno.company.execution import _call
from agno.company.patches import _patch_path, aread_task_patch
from agno.context.wiki import git_ops
from agno.db.schemas.tasks import task_run_id
from agno.sandbox.repository import validate_repository


@asynccontextmanager
async def _publication_lock(db: Any, task_id: str):
    """Serialize publishers across replicas; process death releases the lock."""
    url = db.db_engine.url
    identity = ":".join(
        str(value or "")
        for value in (
            db.db_engine.dialect.name,
            url.host,
            url.port,
            url.database,
            getattr(db, "db_schema", ""),
            db.tasks_table_name,
            task_id,
        )
    )
    digest = hashlib.sha256(identity.encode()).digest()
    if db.db_engine.dialect.name == "postgresql":
        from sqlalchemy import text

        from agno.db.base import AsyncBaseDb

        statement = text("SELECT pg_try_advisory_xact_lock(:key)")
        parameters = {"key": int.from_bytes(digest[:8], "big", signed=True)}
        engine = db.db_engine
        if isinstance(db, AsyncBaseDb):
            async with engine.begin() as connection:
                if not (await connection.execute(statement, parameters)).scalar():
                    raise ValueError("Another publication is in progress")
                yield
        else:
            connection = await asyncio.to_thread(db.db_engine.connect)
            try:
                if not await asyncio.to_thread(lambda: connection.execute(statement, parameters).scalar()):
                    raise ValueError("Another publication is in progress")
                yield
            finally:
                await asyncio.shield(asyncio.to_thread(connection.close))
    else:
        # SQLite is local development storage. flock also fences separate local workers.
        import fcntl

        path = Path(tempfile.gettempdir()) / ("agno-company-publish-" + digest.hex() + ".lock")
        with path.open("a") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError("Another publication is in progress") from None
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


def _source(task: Dict[str, Any], source: Any, *, publishing: bool) -> tuple[str, str, str]:
    checkout = (task.get("metadata") or {}).get("checkout") or {}
    if (
        not source
        or source["type"] != "git"
        or source["product_id"] != task["product_id"]
        or source["reference"] != checkout.get("url")
    ):
        raise ValueError("Task checkout requires its original Product git Source")
    config = source.get("config") or {}
    url, base = source["reference"], config.get("branch", "main")
    validate_repository({"url": url, "branch": base})
    if not re.fullmatch(r"[0-9a-f]{40}", str(checkout.get("commit", ""))):
        raise ValueError("Task checkout requires a pinned commit")
    ref = (
        config.get("publish_credential_ref")
        if publishing
        else source.get("credential_ref") or config.get("publish_credential_ref")
    )
    if publishing and (not ref or ref in {source.get("credential_ref"), "GITHUB_READ_TOKEN"}):
        raise ValueError("Source requires a separate publish_credential_ref")
    token = os.environ.get(ref, "") if ref else ""
    if not token:
        raise ValueError(
            "Source publication credential is unset" if publishing else "Source review credential is unset"
        )
    return url, base, token


def _github(token: str):
    from agno.tools.github import GithubTools

    return GithubTools(access_token=token)


class _SecretFilter(logging.Filter):
    def __init__(self, scrubber: git_ops.Scrubber):
        super().__init__()
        self.scrubber = scrubber
        self.thread = threading.get_ident()

    def filter(self, record: logging.LogRecord) -> bool:
        if record.thread == self.thread:
            record.msg = self.scrubber.scrub(record.getMessage())
            record.args = ()
            if record.exc_info:
                record.msg += ": " + self.scrubber.scrub(str(record.exc_info[1]))
                record.exc_info = None
                record.exc_text = None
        return True


async def _api(github: Any, method: str, scrubber: git_ops.Scrubber, *args: Any, **kwargs: Any):
    def invoke():
        from agno.tools.github import logger as github_logger
        from agno.utils.log import logger

        guard = _SecretFilter(scrubber)
        # Toolkit modules retain the logger imported at construction time, while
        # Team/Workflow execution may switch the current default logger later.
        loggers = {logger, github_logger, logging.getLogger("github.Requester")}
        for target in loggers:
            target.addFilter(guard)
        try:
            value = getattr(github, method)(*args, **kwargs)
            result = json.loads(scrubber.scrub(value))
            if isinstance(result, dict) and result.get("error"):
                raise ValueError("GitHub publication request failed: " + str(result["error"]))
            return result
        except Exception as exc:
            raise ValueError(scrubber.scrub(str(exc))) from None
        finally:
            for target in loggers:
                target.removeFilter(guard)

    pending = asyncio.create_task(asyncio.to_thread(invoke))
    try:
        return await asyncio.shield(pending)
    except asyncio.CancelledError:
        # Keep the publication lock until a mutating API call has finished.
        # Otherwise a retry could create a second PR while the first call is still running.
        try:
            await asyncio.shield(pending)
        finally:
            raise


def _git_env(url: str, token: str) -> Dict[str, str]:
    return {
        **git_ops._credential_env(url, token),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "LC_ALL": "C",
    }


async def _git(args: list[str], directory: Path, env: Dict[str, str], scrubber: git_ops.Scrubber, check: bool = True):
    return await git_ops.run(
        [
            "-c",
            "core.hooksPath=" + os.devnull,
            "-c",
            "core.attributesFile=" + os.devnull,
            "-c",
            "core.autocrlf=false",
            *args,
        ],
        cwd=directory,
        env=env,
        scrubber=scrubber,
        check=check,
        inherit_env=False,
    )


def _previous_pr(task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for result in [task.get("result"), *[entry.get("previous_result") for entry in reversed(task["transitions"])]]:
        if result and result.get("pr"):
            return result["pr"]
    return None


async def _policy(db: Any, task: Dict[str, Any], schedule_db: Any):
    from agno.company.routines import _check_automatic_policy

    acceptances = [entry for entry in task["transitions"] if entry.get("target") == "ready"]
    receipt = acceptances[-1].get("auto_accept") if acceptances else None
    if receipt is None:
        return None
    await _check_automatic_policy(schedule_db or db, task)
    schedule = await _call(schedule_db or db, "get_schedule", receipt["routine_id"])
    return schedule["payload"]["metadata"]["auto_accept"]


async def _checks(policy: Any, manager: Any, task: Dict[str, Any], checks: Any) -> None:
    from copy import deepcopy

    if checks is None:
        from agno.company.routines import _executor_registered, _has_source_evidence, _project_active

        checks = {
            "executor_registered": _executor_registered,
            "has_source_evidence": _has_source_evidence,
            "project_active": _project_active,
        }
    for name in (policy or {}).get("required_checks", []):
        check = (checks or {}).get(name)
        if check is None:
            raise ValueError("Unknown automatic acceptance check: " + name)
        else:
            outcome = (
                await check(deepcopy(task), manager)
                if inspect.iscoroutinefunction(check)
                else await asyncio.to_thread(check, deepcopy(task), manager)
            )
            if inspect.isawaitable(outcome):
                outcome = await outcome
            if outcome is not True:
                raise ValueError("Required publication check failed: " + name)


async def apublish_task(
    db: Any,
    task_id: str,
    attempt: Optional[int] = None,
    *,
    schedule_db: Any = None,
    manager: Any = None,
    checks: Any = None,
    task_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Publish one stored attempt with host-held credentials and return its PR fields."""
    from agno.run.authorization import current_authorization

    authority = current_authorization()
    if authority is not None:
        await authority.arequire("tasks", "write")
        await authority.arequire("sources", "publish")
    async with _publication_lock(db, task_id):
        task = await _call(db, "get_task", task_id)
        if task is None:
            raise LookupError("Task not found")
        if task["status"] != "in_review":
            raise ValueError("Only In review Tasks may be published")
        latest = max((entry["attempt"] for entry in task["transitions"] if "attempt" in entry), default=0)
        selected = latest if attempt is None else attempt
        if type(selected) is not int or not 0 < selected <= latest:
            raise ValueError("Task has no patch for this attempt")
        patch = await aread_task_patch(db, task, selected)
        if not patch:
            raise ValueError("Task has no nonempty patch for this attempt")
        candidates = [task.get("result") or {}, *[entry.get("previous_result") or {} for entry in task["transitions"]]]
        artifact = next((item for item in candidates if item.get("patch_path") == _patch_path(task_id, selected)), None)
        if not artifact or hashlib.sha256(patch.encode()).hexdigest() != artifact.get("patch_sha256"):
            raise ValueError("Task patch digest does not match its stored attempt")
        checkout = (task.get("metadata") or {}).get("checkout") or {}
        source = await _call(db, "get_source", checkout.get("source_id", ""))
        url, base, token = _source(task, source, publishing=True)
        branch = "company/task-" + task_id
        validate_repository({"url": url, "branch": branch})
        scrubber = git_ops.Scrubber([token])
        if manager is None:
            from agno.company.manager import AsyncCompanyManager, CompanyManager
            from agno.db.base import AsyncBaseDb

            manager = (AsyncCompanyManager if isinstance(db, AsyncBaseDb) else CompanyManager)(db)
        policy = await _policy(db, task, schedule_db)
        await _checks(policy, manager, {**task, "result": artifact}, checks)
        github = _github(token)
        repo = url.removeprefix("https://github.com/").removesuffix(".git")
        env = _git_env(url, token)
        with tempfile.TemporaryDirectory(prefix="company-publish-") as temporary:
            directory = Path(temporary)
            await _git(["init", "--template=", "."], directory, env, scrubber)
            await _git(["remote", "add", "origin", url], directory, env, scrubber)
            await _git(["fetch", "--depth=1", "origin", checkout["commit"]], directory, env, scrubber)
            await _git(["checkout", "--detach", checkout["commit"]], directory, env, scrubber)
            patch_file = directory / ".git" / "task.patch"
            patch_file.write_bytes(patch.encode())
            await _git(["apply", "--index", str(patch_file)], directory, env, scrubber)
            entry = next(row for row in task["transitions"] if row.get("attempt") == selected)
            # Stable identity, timestamps and message make retries recreate the same commit.
            env.update(
                {
                    "GIT_AUTHOR_NAME": "Company",
                    "GIT_AUTHOR_EMAIL": "company@localhost",
                    "GIT_COMMITTER_NAME": "Company",
                    "GIT_COMMITTER_EMAIL": "company@localhost",
                    "GIT_AUTHOR_DATE": str(entry["created_at"]) + " +0000",
                    "GIT_COMMITTER_DATE": str(entry["created_at"]) + " +0000",
                }
            )
            message = (
                task["title"].splitlines()[0]
                + "\n\nTask: "
                + task_id
                + "\nAttempt: "
                + str(selected)
                + "\nRun: "
                + task_run_id(task_id, selected)
            )
            await _git(["-c", "commit.gpgSign=false", "commit", "-m", message], directory, env, scrubber)
            head = (await _git(["rev-parse", "HEAD"], directory, env, scrubber)).stdout.strip()
            remote = (
                await _git(["ls-remote", "--heads", "origin", "refs/heads/" + branch], directory, env, scrubber)
            ).stdout.strip()
            remote_sha = remote.split()[0] if remote else ""
            prior = _previous_pr(task)
            existing = await _api(github, "find_pull_request", scrubber, repo, branch)
            if existing is None and prior:
                existing = await _api(github, "get_pull_request_state", scrubber, repo, prior["number"])
            if existing is None:
                existing = await _api(github, "find_pull_request", scrubber, repo, branch, state="all")
            recovering = bool(existing and existing["state"] != "open")
            if recovering:
                existing = await _api(github, "get_pull_request_state", scrubber, repo, existing["number"])
                if not existing["merged"] or not _matches_publication(
                    existing, {"head_sha": head, "branch": branch, "base": base}, repo
                ):
                    raise ValueError("Task pull request is closed; human action is required")
            # Recheck the Task and policy immediately before the first external mutation.
            if await _call(db, "get_task", task_id) != task:
                raise ValueError("Task changed during publication")
            await _policy(db, task, schedule_db)
            if authority is not None:
                await authority.arequire("tasks", "write")
                await authority.arequire("sources", "publish")
            if recovering:
                response = existing
            else:
                if remote_sha != head:
                    await _git(
                        [
                            "push",
                            "--force-with-lease=refs/heads/" + branch + ":" + remote_sha,
                            "origin",
                            "HEAD:refs/heads/" + branch,
                        ],
                        directory,
                        env,
                        scrubber,
                    )
                body = (
                    (task.get("brief") or "")
                    + "\n\n"
                    + str(artifact.get("summary") or "")
                    + "\n\n[Company Task]("
                    + (task_url or "agno://company/tasks/" + task_id)
                    + ")\n\nAttempt: "
                    + str(selected)
                )
                if existing:
                    response = await _api(
                        github,
                        "update_pull_request",
                        scrubber,
                        repo,
                        existing["number"],
                        title=task["title"],
                        body=body,
                        base=base,
                    )
                else:
                    response = await _api(
                        github, "create_pull_request", scrubber, repo, task["title"], body, branch, base
                    )
            pr = {
                "number": response["number"],
                "url": response.get("url") or response["html_url"],
                "head_sha": head,
                "base": base,
                "branch": branch,
            }
        result = {**(task.get("result") or {}), "pr": pr, "published_attempt": selected}
        if not prior or prior["head_sha"] != head:
            result.pop("review_evidence", None)
            result.pop("pr_observation", None)
            result.pop("merge_commit", None)
        saved = await _call(db, "update_task_publication", task, result)
        if saved is None:
            raise ValueError("Task changed during publication; retry to reconcile the published branch")
        if recovering:
            await _reconcile_task(db, saved)
        return pr


def publish_task(db: Any, task_id: str, attempt: Optional[int] = None, **kwargs: Any) -> Dict[str, Any]:
    """Synchronous twin of apublish_task."""
    return asyncio.run(apublish_task(db, task_id, attempt, **kwargs))


async def areconcile_task(db: Any, task_id: str) -> Optional[Dict[str, Any]]:
    """Complete only when the merged commit contains the recorded publication head."""
    from agno.run.authorization import current_authorization

    authority = current_authorization()
    if authority is not None:
        await authority.arequire("tasks", "write")
    async with _publication_lock(db, task_id):
        task = await _call(db, "get_task", task_id)
        if not task or task["status"] != "in_review" or not (task.get("result") or {}).get("pr"):
            return task
        return await _reconcile_task(db, task)


def _matches_publication(state: Dict[str, Any], pr: Dict[str, Any], repo: str) -> bool:
    return (
        state["head_sha"] == pr["head_sha"]
        and state["branch"] == pr["branch"]
        and (state.get("head_repo") or "").casefold() == repo.casefold()
        and state["base"] == pr["base"]
    )


async def _reconcile_task(db: Any, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Reconcile a snapshot while its caller holds the Task publication lock."""
    pr = task["result"]["pr"]
    source = await _call(db, "get_source", task["metadata"]["checkout"]["source_id"])
    url, _, token = _source(task, source, publishing=False)
    scrubber = git_ops.Scrubber([token])
    repo = url.removeprefix("https://github.com/").removesuffix(".git")
    state = await _api(_github(token), "get_pull_request_state", scrubber, repo, pr["number"])
    verified = False
    observation = {
        "state": state["state"],
        "merged": state["merged"],
        "head_sha": state["head_sha"],
        "merge_commit": state["merge_commit"],
        "recorded_head": pr["head_sha"],
        "branch": state["branch"],
        "head_repo": (state.get("head_repo") or "").casefold(),
        "base": state["base"],
    }
    previous = task["result"].get("pr_observation") or {}
    if previous == {**observation, "verified_head": False}:
        return task
    if state["merged"] and state.get("merge_commit"):
        sha = state["merge_commit"]
        if not re.fullmatch(r"[0-9a-f]{40}", sha) or not re.fullmatch(r"[0-9a-f]{40}", pr["head_sha"]):
            raise ValueError("GitHub returned an invalid commit")
        if _matches_publication(state, pr, repo):
            env = _git_env(url, token)
            with tempfile.TemporaryDirectory(prefix="company-verify-") as temporary:
                directory = Path(temporary)
                await _git(["init", "--template=", "."], directory, env, scrubber)
                # Full ancestry is needed to prove containment; publication uses shallow fetches.
                await _git(["fetch", url, sha], directory, env, scrubber)
                # Fetch the head as well: a squash merge does not make its object reachable.
                await _git(["fetch", "--depth=1", url, pr["head_sha"]], directory, env, scrubber)
                result = await _git(
                    ["merge-base", "--is-ancestor", pr["head_sha"], sha], directory, env, scrubber, check=False
                )
                if result.returncode not in (0, 1):
                    raise ValueError("Could not verify merge ancestry")
                verified = result.returncode == 0
        observation["verified_head"] = verified
    result = {**task["result"], "pr_observation": observation}
    if verified:
        result["merge_commit"] = state["merge_commit"]
    if result == task["result"]:
        return task
    return await _call(db, "update_task_publication", task, result, verified_merge=verified)


def reconcile_task(db: Any, task_id: str) -> Optional[Dict[str, Any]]:
    """Synchronous twin of areconcile_task."""
    return asyncio.run(areconcile_task(db, task_id))

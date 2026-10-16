"""Project completed repository checkpoints into durable Company patch files."""

import hashlib
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict

from agno.company.checkpoints import open_run_checkpoint
from agno.context.wiki.git_ops import Scrubber, run
from agno.fs import FileSystem
from agno.sandbox.checkpoint import CheckpointArchive


def _filesystem(db: Any, product_id: str, max_bytes: int = 2 * 1024 * 1024) -> FileSystem:
    return FileSystem(db, namespace=f"company/products/{product_id}/wiki", user_scoped=False, max_file_bytes=max_bytes)


def _patch_path(task_id: str, attempt: int) -> str:
    if not task_id or "/" in task_id or "\\" in task_id or task_id in {".", ".."}:
        raise ValueError("Invalid Task patch identifier")
    if type(attempt) is not int or attempt < 1:
        raise ValueError("Patch attempt must be positive")
    return f"patches/{task_id}/{attempt}.patch"


async def _extract_patch(
    repository: Path, commit: str, max_bytes: int = 2 * 1024 * 1024
) -> tuple[str, list[Dict[str, Any]]]:
    if not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ValueError("Task checkout has no valid pinned commit")
    git = repository / ".git"
    if repository.is_symlink() or not git.is_dir() or git.is_symlink():
        raise ValueError("Checkpoint has no workspace/repository Git checkout")
    # Git state was written by the executor. Never execute its hooks, filters,
    # helpers, includes or filesystem monitors on the host.
    if any(path.is_symlink() for path in git.rglob("*")):
        raise ValueError("Checkpoint Git metadata contains a symlink")
    (git / "config").write_text("[core]\nrepositoryformatversion = 0\nbare = false\nfilemode = true\n")
    for name in ("objects/info/alternates", "objects/info/http-alternates", "config.worktree"):
        (git / name).unlink(missing_ok=True)
    env = {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_CONFIG_COUNT": "0",
        "GIT_CONFIG_PARAMETERS": "",
        "GIT_CONFIG": "/dev/null",
        "GIT_DIR": str(git),
        "GIT_COMMON_DIR": str(git),
        "GIT_WORK_TREE": str(repository),
        "GIT_INDEX_FILE": str(git / "company-index"),
        "GIT_OBJECT_DIRECTORY": str(git / "objects"),
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": "",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_EXTERNAL_DIFF": "",
        "LC_ALL": "C",
    }
    options = ["-c", "core.hooksPath=/dev/null", "-c", "core.attributesFile=/dev/null", "-c", "core.autocrlf=false"]

    async def command(args: list[str]) -> str:
        return (await run(options + args, cwd=repository, env=env, scrubber=Scrubber())).stdout

    head = (await command(["rev-parse", "--verify", "HEAD"])).strip()
    if head != commit:
        raise ValueError(f"Checkpoint HEAD {head} differs from Task checkout commit {commit}")
    (git / "company-index").unlink(missing_ok=True)
    await command(["read-tree", commit])
    for nested in repository.rglob(".git"):
        if nested != git:
            raise ValueError(
                f"Checkpoint contains unsupported nested repository: {nested.parent.relative_to(repository)}"
            )
    for entry in (await command(["ls-files", "--stage", "-z"])).split("\0"):
        if entry.startswith("160000 "):
            raise ValueError(f"Checkpoint contains unsupported nested repository: {entry.split(chr(9), 1)[1]}")
    await command(["add", "--all", "--", "."])
    args = ["diff", "--cached", "--no-ext-diff", "--no-textconv", "--no-renames"]
    # Write the patch directly: diagnostic scrubbing must never alter artifact bytes.
    patch_file = git / "company.patch"
    patch_args = args + [
        "--binary",
        "--full-index",
        "--src-prefix=a/",
        "--dst-prefix=b/",
        "--output=" + str(patch_file),
        commit,
        "--",
    ]
    await command(patch_args)
    try:
        patch = patch_file.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        # The Company filesystem stores text. Encode all changes as Git binary
        # deltas when textual hunks cannot be stored losslessly as UTF-8.
        (git / "info").mkdir(exist_ok=True)
        (git / "info/attributes").write_text("* -diff\n", encoding="utf-8")
        await command(patch_args)
        patch = patch_file.read_bytes().decode("utf-8")
    size = patch_file.stat().st_size
    if size > max_bytes:
        raise ValueError(f"Task patch is {size} bytes, exceeding max_patch_bytes={max_bytes}")
    names = (await command(args + ["--name-status", "-z", commit, "--"])).rstrip("\0").split("\0")
    stats = (await command(args + ["--numstat", "-z", commit, "--"])).rstrip("\0").split("\0")
    counts = {}
    for row in stats:
        if row:
            added, removed, path = row.split("\t", 2)
            counts[path] = (None if added == "-" else int(added), None if removed == "-" else int(removed))
    changed = []
    if names != [""]:
        for status, path in zip(names[::2], names[1::2]):
            added_count, removed_count = counts[path]
            changed.append({"path": path, "status": status, "added": added_count, "removed": removed_count})
    return patch, changed


async def _project_patch(
    db: Any, task: Dict[str, Any], agent: Any, data: Dict[str, Any], checkout: Dict[str, Any], max_bytes: int
) -> Dict[str, Any]:
    attempt = max(entry["attempt"] for entry in task["transitions"] if "attempt" in entry)
    async with open_run_checkpoint(agent, data) as archive:
        with TemporaryDirectory(prefix="company-patch-") as temporary:
            destination = Path(temporary) / "checkpoint"
            await CheckpointArchive().arestore(archive, destination)
            patch, changed = await _extract_patch(destination / "workspace/repository", checkout["commit"], max_bytes)
    size = len(patch.encode("utf-8"))
    if size > max_bytes:
        raise ValueError(f"Task patch is {size} bytes, exceeding max_patch_bytes={max_bytes}")
    path = _patch_path(task["id"], attempt)
    await _filesystem(db, task["product_id"], max_bytes).awrite(path, patch)
    return {
        "patch_path": path,
        "patch_sha256": hashlib.sha256(patch.encode("utf-8")).hexdigest(),
        "changed_files": changed,
        "summary": data.get("content"),
    }


def read_task_patch(db: Any, task: Dict[str, Any], attempt: int) -> str | None:
    """Read a stored attempt's patch, including an empty patch."""
    return _filesystem(db, task["product_id"]).read(_patch_path(task["id"], attempt))


async def aread_task_patch(db: Any, task: Dict[str, Any], attempt: int) -> str | None:
    """Async twin of :func:`read_task_patch`."""
    return await _filesystem(db, task["product_id"]).aread(_patch_path(task["id"], attempt))

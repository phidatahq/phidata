"""Write Agno-owned state into a harness home directory before a run.

Claude Code and Codex read skills from ``<home>/skills/<name>/SKILL.md`` and user-level
instructions from ``<home>/CLAUDE.md`` or ``<home>/AGENTS.md``. Agno keeps skills and user
memories in its own objects and database; these helpers copy that state into the home so the
harness discovers it natively, and remove what Agno wrote earlier that no longer applies.

Only files Agno wrote are touched. Skills are tracked in ``<home>/.agno/skills.json``;
instructions live inside a marked block so content the user keeps in the same file survives.
"""

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional, Sequence

from agno.utils.log import log_warning

if TYPE_CHECKING:
    from agno.skills import Skills

BLOCK_START = "<!-- agno:start -->"
BLOCK_END = "<!-- agno:end -->"
_STATE_DIR = ".agno"
_SKILLS_STATE = "skills.json"


def _skill_frontmatter(skill: Any) -> str:
    lines = ["---", f"name: {skill.name}", f"description: {skill.description}"]
    if skill.license:
        lines.append(f"license: {skill.license}")
    if skill.compatibility:
        lines.append(f"compatibility: {skill.compatibility}")
    if skill.allowed_tools:
        lines.append(f"allowed-tools: {' '.join(skill.allowed_tools)}")
    lines.append("---")
    return "\n".join(lines)


def _copy_folder(source: Path, target: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True)


def _read_written_skills(home: Path) -> List[str]:
    state = home / _STATE_DIR / _SKILLS_STATE
    if not state.is_file():
        return []
    try:
        names = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [name for name in names if isinstance(name, str)] if isinstance(names, list) else []


def _write_written_skills(home: Path, names: Sequence[str]) -> None:
    state_dir = home / _STATE_DIR
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / _SKILLS_STATE).write_text(json.dumps(sorted(names)), encoding="utf-8")


def materialize_skills(home: Path, skills: "Skills") -> List[str]:
    """Write each skill as ``<home>/skills/<name>/`` and return the names written.

    Skills Agno wrote on an earlier run that are no longer present are removed. Folders
    under ``skills/`` that Agno never wrote are left alone.
    """
    skills_root = home / "skills"
    previous = set(_read_written_skills(home))
    written: List[str] = []
    for skill in skills.get_all_skills():
        folder = skills_root / skill.name
        if folder.exists() and skill.name not in previous:
            log_warning(f"Skill folder {folder} was not written by Agno; leaving it unchanged.")
            continue
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
        body = skill.instructions.strip()
        (folder / "SKILL.md").write_text(f"{_skill_frontmatter(skill)}\n\n{body}\n", encoding="utf-8")
        source = Path(skill.source_path) if skill.source_path else None
        if source is not None and source.is_dir():
            _copy_folder(source / "scripts", folder / "scripts")
            _copy_folder(source / "references", folder / "references")
        written.append(skill.name)
    for stale in previous - set(written):
        shutil.rmtree(skills_root / stale, ignore_errors=True)
    written.sort()
    _write_written_skills(home, written)
    return written


def remove_materialized_skills(home: Path) -> None:
    """Remove every skill Agno wrote into the home."""
    for name in _read_written_skills(home):
        shutil.rmtree(home / "skills" / name, ignore_errors=True)
    _write_written_skills(home, [])


def write_managed_block(path: Path, content: Optional[str]) -> None:
    """Replace, add or remove the Agno block in an instructions file, keeping the rest."""
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    start = existing.find(BLOCK_START)
    end = existing.find(BLOCK_END)
    if start != -1 and end != -1 and end > start:
        before = existing[:start].rstrip("\n")
        after = existing[end + len(BLOCK_END) :].lstrip("\n")
    else:
        before, after = existing.rstrip("\n"), ""
    if content is None:
        if start == -1:
            return
        parts = [part for part in (before, after) if part]
        if parts:
            path.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
        else:
            path.unlink(missing_ok=True)
        return
    block = f"{BLOCK_START}\n{content.strip()}\n{BLOCK_END}"
    parts = [part for part in (before, block, after) if part]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n\n".join(parts) + "\n", encoding="utf-8")


def memories_block(memories: Optional[Sequence[Any]]) -> Optional[str]:
    """Format user memories as a section for the harness instructions file."""
    if not memories:
        return None
    lines = ["## What you remember about this user", ""]
    for memory in memories:
        text = getattr(memory, "memory", None) or str(memory)
        lines.append(f"- {text.strip()}")
    return "\n".join(lines)

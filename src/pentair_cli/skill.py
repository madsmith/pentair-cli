"""Locate and install the bundled agent skill."""

from __future__ import annotations

import shutil
from pathlib import Path

from pentair_cli import __version__

SKILL_NAME = "pentair"
DEFAULT_SKILLS_DIR = Path("~/.claude/skills")


def bundled_skill_dir() -> Path:
    here = Path(__file__).resolve().parent
    # Wheel install: force-included as pentair_cli/_skill
    packaged = here / "_skill"
    if (packaged / "SKILL.md").is_file():
        return packaged
    # Source / editable checkout: <repo>/skill
    source = here.parents[1] / "skill"
    if (source / "SKILL.md").is_file():
        return source
    raise FileNotFoundError("Bundled skill not found; reinstall pentair-cli")


def install(dest: str | Path | None = None, force: bool = False) -> Path:
    skills_dir = Path(dest).expanduser() if dest else DEFAULT_SKILLS_DIR.expanduser()
    target = skills_dir / SKILL_NAME
    if target.exists():
        if not force:
            raise FileExistsError(str(target))
        shutil.rmtree(target)
    skills_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bundled_skill_dir(), target)
    # Record which CLI build installed this copy, so drift is detectable.
    (target / "VERSION").write_text(__version__ + "\n", encoding="utf-8")
    return target

"""Skill discovery — find skills on disk and build a library.

Two search locations, in load order:

1. The **built-in library** shipped in ``skills/`` next to the project.
2. The **installed library** — by default ``./.agents/skills`` (the
   convention most coding agents use for project-level skills).

Installed skills override built-ins *by name*. That is deliberate: it makes
``skill-forge install`` an upgrade path — drop in a better version of a skill
and it replaces the stock one, the same way ``pip install --upgrade`` works.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .skill import Skill, SkillParseError, load_skill

DEFAULT_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
DEFAULT_INSTALL_DIR = Path.cwd() / ".agents" / "skills"


@dataclass
class SkillLibrary:
    """A name-indexed collection of skills plus where each one came from."""

    skills: dict[str, Skill] = field(default_factory=dict)
    overrides: list[str] = field(default_factory=list)  # names that shadowed a built-in

    def add(self, skill: Skill) -> None:
        if skill.name in self.skills:
            self.overrides.append(skill.name)
        self.skills[skill.name] = skill

    def get(self, name: str) -> Skill:
        try:
            return self.skills[name]
        except KeyError:
            known = ", ".join(sorted(self.skills))
            raise KeyError(f"No skill named {name!r}. Known skills: {known}") from None

    def all(self) -> list[Skill]:
        return sorted(self.skills.values(), key=lambda s: s.name)

    def __len__(self) -> int:
        return len(self.skills)


def discover(directory: Path, *, strict: bool = True) -> list[Skill]:
    """Load every skill folder inside ``directory``.

    A skill folder is any immediate subdirectory containing a ``SKILL.md``.
    Folders without one are skipped (they're probably assets). With
    ``strict=True`` a malformed SKILL.md raises; otherwise it is skipped and
    reported on stderr — useful when scanning a user's install directory so
    one bad file doesn't brick the whole CLI.
    """
    import sys

    found: list[Skill] = []
    if not directory.exists():
        return found

    for child in sorted(directory.iterdir()):
        if not child.is_dir() or not (child / "SKILL.md").exists():
            continue
        try:
            found.append(load_skill(child))
        except SkillParseError as exc:
            if strict:
                raise
            print(f"[warn] skipping {child.name}: {exc}", file=sys.stderr)
    return found


def load_library(
    builtin_dir: Path | None = None,
    install_dir: Path | None = None,
) -> SkillLibrary:
    """Build the merged library (built-ins first, installed override)."""
    lib = SkillLibrary()
    for skill in discover(builtin_dir or DEFAULT_SKILLS_DIR):
        lib.add(skill)
    if install_dir is not None:
        for skill in discover(install_dir, strict=False):
            lib.add(skill)
    else:
        # Also pick up a project-local .agents/skills if the user runs the
        # CLI from somewhere that has one — same convention as the install
        # command, so installed skills are visible without extra flags.
        for skill in discover(DEFAULT_INSTALL_DIR, strict=False):
            lib.add(skill)
    return lib

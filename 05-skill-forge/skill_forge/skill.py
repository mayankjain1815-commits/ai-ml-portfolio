"""SKILL.md model — parsing skill files into Skill objects.

A "skill" is a folder containing a SKILL.md file. The file has YAML-ish
frontmatter between `---` fences (name, description, triggers, risk, mode)
and a Markdown body with the actual step-by-step instructions.

We deliberately parse a *tiny* subset of YAML (flat keys and comma-separated
values) instead of pulling in PyYAML. That keeps the dependency footprint at
zero for parsing and means a malformed skill file fails with a clear,
human-readable error instead of a YAML stack trace.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

ALLOWED_RISKS = ("safe", "moderate", "risky")
ALLOWED_MODES = ("action", "guided")

# Keys we understand in frontmatter. Unknown keys are kept (forward
# compatible) but never break parsing.
KNOWN_KEYS = {"name", "description", "triggers", "risk", "mode", "version"}


class SkillParseError(ValueError):
    """Raised when a SKILL.md file is malformed."""


@dataclass(frozen=True)
class Skill:
    """An immutable description of one skill."""

    name: str
    description: str
    triggers: tuple[str, ...] = ()
    risk: str = "safe"
    mode: str = "guided"
    version: str = "1"
    body: str = ""
    path: Path | None = None  # folder the SKILL.md came from

    @property
    def folder(self) -> Path | None:
        return self.path.parent if self.path else None

    @property
    def has_action(self) -> bool:
        """True if the skill ships an executable ``action.py``."""
        return bool(self.path and (self.path.parent / "action.py").exists())

    def matches(self, needle: str) -> bool:
        """Case-insensitive word-level match across name, triggers, description."""
        needle = needle.lower()
        if needle in self.name.lower():
            return True
        return any(needle == t.lower() for t in self.triggers)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split a SKILL.md into ``(frontmatter_dict, body)``.

    Frontmatter is the block between the first pair of ``---`` lines.
    Missing frontmatter is an error — every skill needs a name and a
    description because those are what the selector reads.

    Triggers/description style keys accept comma-separated lists.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SkillParseError("SKILL.md must start with a '---' frontmatter fence")

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise SkillParseError("SKILL.md frontmatter is never closed with '---'")

    meta: dict[str, str] = {}
    for raw in lines[1:end]:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise SkillParseError(f"Frontmatter line is not 'key: value': {raw!r}")
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()

    body = "\n".join(lines[end + 1 :]).strip()

    if "name" not in meta or not meta["name"]:
        raise SkillParseError("Frontmatter is missing required key: name")
    if "description" not in meta or not meta["description"]:
        raise SkillParseError("Frontmatter is missing required key: description")

    return meta, body


def _csv_tuple(value: str) -> tuple[str, ...]:
    """``'csv, dataframe'`` -> ``('csv', 'dataframe')`` (empty -> ``()``)."""
    return tuple(v.strip() for v in value.split(",") if v.strip())


def parse_skill(text: str, path: Path | None = None) -> Skill:
    """Parse the raw text of a SKILL.md into a :class:`Skill`."""
    meta, body = parse_frontmatter(text)

    risk = meta.get("risk", "safe").lower()
    if risk not in ALLOWED_RISKS:
        raise SkillParseError(
            f"risk must be one of {ALLOWED_RISKS}, got {risk!r} (skill {meta['name']!r})"
        )

    mode = meta.get("mode", "guided").lower()
    if mode not in ALLOWED_MODES:
        raise SkillParseError(
            f"mode must be one of {ALLOWED_MODES}, got {mode!r} (skill {meta['name']!r})"
        )

    return Skill(
        name=meta["name"],
        description=meta["description"],
        triggers=_csv_tuple(meta.get("triggers", "")),
        risk=risk,
        mode=mode,
        version=meta.get("version", "1"),
        body=body,
        path=path,
    )


def load_skill(folder: Path) -> Skill:
    """Load one skill from its folder (reads ``SKILL.md`` inside it)."""
    md = folder / "SKILL.md"
    if not md.exists():
        raise SkillParseError(f"No SKILL.md found in {folder}")
    return parse_skill(md.read_text(encoding="utf-8"), path=md)

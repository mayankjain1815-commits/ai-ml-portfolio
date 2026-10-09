"""Tests for SKILL.md parsing — the format contract every skill obeys."""

from pathlib import Path

import pytest

from skill_forge.skill import (
    SkillParseError,
    load_skill,
    parse_frontmatter,
    parse_skill,
)

VALID = """---
name: demo-skill
description: A skill used only in tests.
triggers: demo, test, sample
risk: safe
mode: action
---

# Demo Skill

Do the thing.
"""


def test_parse_valid_frontmatter():
    meta, body = parse_frontmatter(VALID)
    assert meta["name"] == "demo-skill"
    assert "Do the thing." in body


def test_missing_opening_fence_raises():
    with pytest.raises(SkillParseError, match="start with"):
        parse_frontmatter("# no frontmatter here")


def test_unclosed_fence_raises():
    with pytest.raises(SkillParseError, match="never closed"):
        parse_frontmatter("---\nname: x\ndescription: y\n")


def test_missing_required_keys_raise():
    with pytest.raises(SkillParseError, match="name"):
        parse_frontmatter("---\ndescription: only this\n---\nbody")
    with pytest.raises(SkillParseError, match="description"):
        parse_frontmatter("---\nname: only-this\n---\nbody")


def test_bad_frontmatter_line_raises():
    with pytest.raises(SkillParseError, match="not 'key: value'"):
        parse_frontmatter("---\nname: x\ndescription: y\njust some text\n---\n")


def test_parse_skill_fields_and_defaults():
    skill = parse_skill(VALID)
    assert skill.name == "demo-skill"
    assert skill.triggers == ("demo", "test", "sample")
    assert skill.risk == "safe"
    assert skill.mode == "action"
    assert skill.version == "1"


def test_invalid_risk_rejected():
    with pytest.raises(SkillParseError, match="risk"):
        parse_skill("---\nname: x\ndescription: y\nrisk: dangerous\n---\n")


def test_invalid_mode_rejected():
    with pytest.raises(SkillParseError, match="mode"):
        parse_skill("---\nname: x\ndescription: y\nmode: chaos\n---\n")


def test_matches_is_case_insensitive_on_triggers():
    skill = parse_skill(VALID)
    assert skill.matches("csv") is False  # not a trigger of this skill
    assert skill.matches("demo") is True
    assert skill.matches("DEMOS") is False  # word-level, not substring


def test_builtin_library_loads_all_shipped_skills():
    skills_dir = Path(__file__).resolve().parents[1] / "skills"
    names = sorted(
        p.parent.name for p in skills_dir.glob("*/SKILL.md")
    )
    assert len(names) >= 9
    for folder in sorted(skills_dir.iterdir()):
        if (folder / "SKILL.md").exists():
            skill = load_skill(folder)
            assert skill.name == folder.name, "skill name must match its folder"
            assert skill.body, f"{skill.name} has an empty body"
            assert skill.description.endswith(".")


def test_action_skills_ship_executable_actions():
    skills_dir = Path(__file__).resolve().parents[1] / "skills"
    for folder in sorted(skills_dir.iterdir()):
        md = folder / "SKILL.md"
        if not md.exists():
            continue
        skill = load_skill(folder)
        if skill.mode == "action":
            assert skill.has_action, f"{skill.name} declares mode=action but has no action.py"

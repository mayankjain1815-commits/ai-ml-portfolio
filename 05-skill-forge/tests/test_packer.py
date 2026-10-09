"""Packer tests — the context-budget guarantee."""

import pytest

from skill_forge.packer import DEFAULT_BUDGET, estimate_tokens, pack
from skill_forge.skill import parse_skill


def _skill(body: str):
    return parse_skill(f"---\nname: t\ndescription: test skill.\n---\n{body}")


def test_estimate_tokens_scales_with_length():
    assert estimate_tokens("") == 0 or estimate_tokens("") == 1
    assert estimate_tokens("a" * 400) == 100
    assert estimate_tokens("a" * 4) == 1


def test_small_prompt_fits_untruncated():
    packed = pack(_skill("Step one.\nStep two."), "do it")
    assert packed.fitted
    assert packed.truncated_lines == 0
    assert packed.tokens <= packed.budget
    assert packed.utilisation < 1.0
    assert "SKILL: t" in packed.text
    assert "Task: do it" in packed.text


def test_oversized_body_is_truncated_at_line_boundaries():
    body = "\n".join(f"Line {i}: " + "x" * 80 for i in range(200))
    packed = pack(_skill(body), "go", budget=300)
    assert packed.tokens <= 300
    assert packed.truncated_lines > 0
    assert not packed.fitted
    assert "truncated" in packed.text
    # No half-lines: every body line in the output ends with 'x'.
    body_part = packed.text.split("--- SKILL: t ---", 1)[1].split("\n---\n", 1)[0]
    for line in body_part.strip().splitlines():
        assert line.endswith("x")


def test_history_is_included_before_skill():
    packed = pack(_skill("body"), "task", history="user likes brevity")
    assert "user likes brevity" in packed.text
    assert packed.text.index("user likes brevity") < packed.text.index("SKILL: t")


def test_tiny_budget_raises_instead_of_looping_forever():
    with pytest.raises(ValueError, match="at least"):
        pack(_skill("body"), "task", budget=10)


def test_budget_beyond_header_capacity_raises_clear_error():
    with pytest.raises(ValueError, match="exceed"):
        pack(_skill("b"), "x" * 6000, budget=200)


def test_default_budget_is_sane():
    packed = pack(_skill("short body"), "short task")
    assert packed.budget == DEFAULT_BUDGET

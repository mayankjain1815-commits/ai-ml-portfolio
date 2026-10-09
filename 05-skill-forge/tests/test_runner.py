"""Runner + loader tests — skills actually do things, offline."""

from pathlib import Path

import pytest

from skill_forge.loader import discover, load_library
from skill_forge.runner import parse_inputs, run
from skill_forge.skill import load_skill

PROJECT = Path(__file__).resolve().parents[1]
SKILLS_DIR = PROJECT / "skills"
SAMPLE_CSV = PROJECT / "data" / "sample.csv"


def test_parse_inputs_roundtrip():
    assert parse_inputs(["a=1", "b=two words"]) == {"a": "1", "b": "two words"}


def test_parse_inputs_rejects_missing_equals():
    with pytest.raises(ValueError, match="key=value"):
        parse_inputs(["nonsense"])


def test_discover_finds_all_shipped_skills():
    found = discover(SKILLS_DIR)
    assert len(found) >= 9


def test_discover_missing_dir_returns_empty(tmp_path):
    assert discover(tmp_path / "nope") == []


def test_csv_analyzer_action_runs_on_sample_data():
    skill = load_skill(SKILLS_DIR / "csv-analyzer")
    result = run(skill, {"path": str(SAMPLE_CSV)})
    assert result.ok and result.mode == "action"
    assert "SHAPE" in result.output
    assert "24 rows" in result.output
    # The planted revenue typo (4999 vs ~500 median) must be caught.
    assert "likely a typo" in result.output
    # The planted missing row must be reported.
    assert "missing" in result.output.lower()


def test_csv_analyzer_missing_file_fails_gracefully():
    skill = load_skill(SKILLS_DIR / "csv-analyzer")
    result = run(skill, {"path": "/no/such/file.csv"})
    assert not result.ok
    assert "not found" in result.output
    assert "Traceback" not in result.output


def test_unit_convert_km_to_miles():
    skill = load_skill(SKILLS_DIR / "unit-convert")
    result = run(skill, {"value": "12.5", "from_unit": "km", "to_unit": "miles"})
    assert result.ok
    assert result.output.startswith("12.5 km = 7.767 miles")


def test_unit_convert_temperature_uses_offsets():
    skill = load_skill(SKILLS_DIR / "unit-convert")
    result = run(skill, {"value": "100", "from_unit": "f", "to_unit": "c"})
    assert "37.78" in result.output  # 100F == 37.78C, not 180F-worth of scaling


def test_unit_convert_incompatible_families_reported():
    skill = load_skill(SKILLS_DIR / "unit-convert")
    result = run(skill, {"value": "5", "from_unit": "kg", "to_unit": "km"})
    assert not result.ok or "can't convert" in result.output
    assert "Supported families" in result.output


def test_summarize_text_extractive_and_shorter():
    text = (
        "The James Webb Space Telescope is the largest optical telescope in space. "
        "Its high resolution and sensitivity allow it to view objects too far away "
        "for the Hubble Space Telescope. Webb observes in the infrared, while Hubble "
        "primarily observes in ultraviolet and visible light. Together they give "
        "astronomers a much fuller picture of the universe. "
        "Webb launched on December 25, 2021 and sits at the L2 point, "
        "about 1.5 million kilometers from Earth. Its mirror spans 6.5 meters "
        "and is made of 18 gold-coated beryllium segments. "
        "Because it sees infrared light, Webb can peer through cosmic dust clouds "
        "that block visible-light telescopes. "
        "Astronomers use it to study the earliest galaxies, "
        "star formation, and the atmospheres of distant exoplanets. "
        "The telescope requires regular momentum dumps from its reaction wheels "
        "to stay pointed accurately at its targets."
    )
    skill = load_skill(SKILLS_DIR / "summarize-text")
    result = run(skill, {"text": text})
    assert result.ok
    assert "SUMMARY" in result.output
    assert "KEYWORDS" in result.output
    # Extractive: every summary sentence must come from the source.
    summary = result.output.split("SUMMARY")[1].split("KEYWORDS")[0].strip()
    for sentence in summary.split(". "):
        core = sentence.strip().rstrip(".")
        assert core in text, f"sentence not verbatim from source: {core!r}"


def test_summarize_too_short_says_so():
    skill = load_skill(SKILLS_DIR / "summarize-text")
    result = run(skill, {"text": "Too short. Really short."})
    assert result.ok
    assert "Too short" in result.output


def test_study_plan_is_deterministic_and_balanced():
    skill = load_skill(SKILLS_DIR / "study-plan")
    result = run(skill, {"subjects": "math=3,history=1", "hours": "5", "days": "5"})
    assert result.ok
    assert "WEEKLY STUDY PLAN" in result.output
    assert "math" in result.output and "history" in result.output
    # Same inputs -> identical plan.
    again = run(skill, {"subjects": "math=3,history=1", "hours": "5", "days": "5"})
    assert again.output == result.output


def test_budget_calculator_flags_overspending():
    skill = load_skill(SKILLS_DIR / "budget-calculator")
    result = run(skill, {"income": "1000", "rent": "900", "food": "300"})
    assert result.ok
    assert "OVERSPENDING" in result.output


def test_budget_calculator_on_track_path():
    skill = load_skill(SKILLS_DIR / "budget-calculator")
    result = run(skill, {"income": "3000", "need_rent": "1200",
                         "want_eating_out": "400", "save_emergency": "600"})
    assert result.ok
    assert "VERDICT" in result.output


def test_flashcards_parse_and_order():
    skill = load_skill(SKILLS_DIR / "flashcards")
    cards = "What is RAM? :: Working memory;;What is a CPU? :: The brain"
    result = run(skill, {"cards": cards})
    assert result.ok
    assert "2 cards" in result.output
    assert "SELF-TEST ORDER" in result.output


def test_guided_skill_returns_honest_plan_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    skill = load_skill(SKILLS_DIR / "debug-helper")
    result = run(skill, {"bug": "it crashes"})
    assert result.ok
    assert result.mode == "plan"
    assert "PLAN" in result.output
    assert "Set GEMINI_API_KEY" in result.output
    # The plan must contain the skill's real steps.
    assert "Reproduce." in result.output


def test_library_installed_override(tmp_path):
    install = tmp_path / "skills"
    target = install / "csv-analyzer"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text(
        "---\nname: csv-analyzer\ndescription: New and improved.\n---\nNew body.",
        encoding="utf-8",
    )
    lib = load_library(install_dir=install)
    assert lib.get("csv-analyzer").description == "New and improved."
    assert "csv-analyzer" in lib.overrides

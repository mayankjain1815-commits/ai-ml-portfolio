"""Selector tests — why a task picks the skill it picks."""

from skill_forge.loader import load_library
from skill_forge.selector import KeywordSelector, LLMSelector
from skill_forge.skill import parse_skill

LIB = load_library()
SKILLS = LIB.all()


def test_library_contains_shipped_skills():
    assert len(SKILLS) >= 9
    for name in ("csv-analyzer", "unit-convert", "debug-helper"):
        assert LIB.get(name)


def test_csv_task_picks_csv_analyzer():
    sel = KeywordSelector(SKILLS).select("analyze the csv in data/sample.csv")
    assert sel.skill.name == "csv-analyzer"
    assert sel.strategy == "keyword"
    assert sel.confidence in {"medium", "high"}


def test_conversion_task_picks_unit_convert():
    sel = KeywordSelector(SKILLS).select("convert 12.5 km to miles")
    assert sel.skill.name == "unit-convert"


def test_summary_task_picks_summarize_text():
    sel = KeywordSelector(SKILLS).select("can you tldr this article for me")
    assert sel.skill.name == "summarize-text"


def test_unrelated_task_does_not_crash_and_picks_something():
    sel = KeywordSelector(SKILLS).select("purple elephants bicycle qqqzzz")
    assert sel.skill is not None
    assert len(SKILLS) > 0


def test_scores_are_ranked_best_first():
    sel = KeywordSelector(SKILLS).select("build me a study schedule plan")
    scores = [s for _, s in sel.alternatives]
    assert scores == sorted(scores, reverse=True) or len(scores) < 2


def test_llm_selector_without_key_falls_back_to_keyword(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    sel = LLMSelector(SKILLS).select("convert 5 kg to pounds")
    assert sel.skill.name == "unit-convert"
    assert "keyword" in sel.strategy


def test_trigger_word_boundary_no_false_positive():
    # 'cash' contains 'ash' but no skill triggers on 'ash' — make sure a
    # near-miss word doesn't accidentally activate a trigger.
    skill = parse_skill(
        "---\nname: ash-scanner\ndescription: scans ash.\n"
        "triggers: ash\n---\nbody"
    )
    from skill_forge.selector import KeywordSelector as KS

    assert KS([skill]).score("cash deposit", skill) == 0.0
    assert KS([skill]).score("volcanic ash layer", skill) >= 3.0

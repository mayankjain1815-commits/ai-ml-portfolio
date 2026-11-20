import json
import re
from pathlib import Path

from word_atlas.app import validate_data
from word_atlas.data import PALETTE, WORDS, all_words, get_word, related_words

ROOT = Path(__file__).resolve().parents[2]
SLUGS = {w["slug"] for w in WORDS}


def test_data_validates():
    assert validate_data() is True


def test_exactly_the_ten_landing_page_words():
    assert len(WORDS) == 10
    assert SLUGS == {"rag", "agents", "mlops", "forecast", "signals",
                     "skills", "risk", "offline", "demo", "iot"}


def test_every_code_anchor_points_at_a_real_file():
    for word in WORDS:
        for anchor in word["code_anchors"]:
            assert (ROOT / anchor["path"]).is_file(), anchor["path"]
            assert anchor["symbol"] and anchor["note"]


def test_every_project_reference_is_real():
    for word in WORDS:
        for project in word["projects"]:
            assert (ROOT / project["readme"]).is_file(), project["readme"]
            assert project["role"]


def test_colors_come_from_the_palette():
    assert {w["color"] for w in WORDS} <= set(PALETTE.values())


def test_related_is_symmetric_and_self_free():
    for word in WORDS:
        related = related_words(word["slug"])
        assert all(item["slug"] != word["slug"] for item in related)
        for item in related:
            assert word["slug"] in {r["slug"] for r in related_words(item["slug"])}


def test_unknown_word_helpers():
    assert get_word("missing") is None
    assert related_words("missing") == []


def test_landing_page_ring_matches_data():
    html = (ROOT / "index.html").read_text()
    ring = re.search(r'<div class="ring".*?</div>', html, re.S).group(0)
    terms = [w.strip() for w in re.findall(r"<span[^>]*>([^<]+)</span>", ring)]
    assert terms == [w["term"] for w in WORDS]
    assert re.findall(r'data-word="([^"]+)"', ring) == [w["slug"] for w in WORDS]


def test_embedded_fallback_json_matches_data():
    html = (ROOT / "index.html").read_text()
    blob = re.search(
        r'<script type="application/json" id="word-atlas-data">(.*?)</script>',
        html, re.S,
    ).group(1)
    assert json.loads(blob) == all_words()


def test_records_are_deep_enough_to_be_useful():
    for word in WORDS:
        assert len(word["definition"]) > 60
        assert len(word["why_it_matters"]) > 60
        assert len(word["interview_answer"]) > 100
        assert len(word["how_it_works"]) >= 4
        assert len(word["concepts"]) >= 4
        assert len(word["pitfalls"]) >= 3
        assert len(word["commands"]) >= 1

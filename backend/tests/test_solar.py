import json
import re
from pathlib import Path

import pytest

from word_atlas.app import create_app, validate_data
from word_atlas.solar import (
    SOLAR_REQUIRED_FIELDS, all_bodies, get_body, neighbours, solar_payload,
    solar_stats,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_layout_is_deterministic_and_complete():
    bodies = all_bodies()
    assert len(bodies) == 33
    assert sum(b["kind"] == "word" for b in bodies) == 10
    assert sum(b["kind"] == "repo" for b in bodies) == 23
    assert len({(b["kind"], b["slug"]) for b in bodies}) == 33
    assert len({b["catalog_id"] for b in bodies}) == 33
    assert bodies == all_bodies()
    for body in bodies:
        assert all(field in body for field in SOLAR_REQUIRED_FIELDS)
        assert 0 < body["orbit"] < 1
        assert 0 < body["period"] <= 200
        assert body["radius"] > 0
        assert 0 <= body["phase"] < 6.2832
        assert len(body["moon_names"]) == body["moons"]
        assert body["texture"] in {"banded", "cratered", "icy", "stormy", "terran"}


def test_bodies_are_grouped_into_narrow_orbit_bands():
    bodies = all_bodies()
    assert len({b["orbit_band"] for b in bodies if b["kind"] == "word"}) == 5
    assert len({b["orbit_band"] for b in bodies if b["kind"] == "repo"}) == 8
    assert all(b["orbit"] < 0.7 for b in bodies if b["kind"] == "word")
    assert all(b["orbit"] >= 0.7 for b in bodies if b["kind"] == "repo")


def test_helpers_and_stats():
    assert get_body("WORDS", "RAG")["catalog_id"] == "W01"
    assert get_body("repos", "omniroute")["kind"] == "repo"
    assert get_body("planet", "rag") is None
    assert get_body("word", "missing") is None
    rag = get_body("word", "rag")
    assert neighbours(rag) and all(n["slug"] != "rag" for n in neighbours(rag))
    stats = solar_stats()
    assert stats["bodies"] == 33
    assert stats["words"] == 10
    assert stats["repos"] == 23
    assert stats["orbit_bands"] == 13
    assert stats["moons"] == sum(b["moons"] for b in all_bodies())
    assert stats["ring_worlds"] == sum(b["ring"] for b in all_bodies())
    assert validate_data() is True


def test_solar_api_lists_every_body(client):
    r = client.get("/api/solar")
    assert r.status_code == 200
    assert r.json["ok"] is True
    assert len(r.json["bodies"]) == 33
    assert r.json["star"]["label"] == "CORE"
    assert r.json["stats"] == solar_stats()
    assert "deterministic" in r.json["note"]
    assert client.get("/api/solar/stats").json["bodies"] == 33


@pytest.mark.parametrize("body", all_bodies(), ids=lambda b: b["catalog_id"])
def test_solar_detail_for_every_world(client, body):
    r = client.get(f"/api/solar/{body['kind']}s/{body['slug']}")
    assert r.status_code == 200
    data = r.json
    assert data["ok"] is True
    assert data["body"] == body
    assert data["record"]["slug"] == body["slug"]
    assert data["neighbours"]
    if body["kind"] == "word":
        assert data["record"]["definition"]
        assert data["record"]["repos"]
    else:
        assert data["record"]["stack"]
        assert data["record"]["linked_words"]


def test_solar_detail_rejects_unknown_kinds_and_slugs(client):
    assert client.get("/api/solar/moons/rag").status_code == 404
    r = client.get("/api/solar/words/nope")
    assert r.status_code == 404
    assert len(r.json["available"]) == 10


def test_embedded_solar_json_matches_the_backend():
    html = (ROOT / "index.html").read_text()
    blob = re.search(
        r'<script type="application/json" id="solar-atlas-data">(.*?)</script>',
        html, re.S,
    ).group(1)
    assert json.loads(blob) == solar_payload()


def test_html_has_a_canvas_and_a_button_for_every_world():
    html = (ROOT / "index.html").read_text()
    assert 'id="fx-solar"' in html
    assert 'id="solar-atlas-data"' in html
    assert 'id="fx-snow"' not in html
    for body in all_bodies():
        assert f'data-{body["kind"]}="{body["slug"]}"' in html

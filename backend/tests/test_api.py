import pytest

from word_atlas.app import create_app

SLUGS = ["rag", "agents", "mlops", "forecast", "signals", "skills", "risk", "offline", "demo", "iot"]


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json["ok"] is True
    assert r.json["service"] == "word-atlas"
    assert r.json["words"] == 10
    assert r.json["repos"] == 23
    assert r.json["bodies"] == 33
    assert r.json["themes"] == 1
    assert r.json["offline"] is True


@pytest.mark.parametrize("slug", SLUGS)
def test_detail_for_every_word(client, slug):
    r = client.get(f"/api/words/{slug}")
    assert r.status_code == 200
    assert r.json["ok"] is True
    assert r.json["word"]["slug"] == slug
    assert r.json["word"]["how_it_works"]
    assert r.json["word"]["interview_answer"]


def test_detail_is_case_insensitive(client):
    assert client.get("/api/words/RAG").json["word"]["slug"] == "rag"


def test_unknown_word_lists_available_slugs(client):
    r = client.get("/api/words/nope")
    assert r.status_code == 404
    assert r.json["available"] == SLUGS


def test_words_list_shape(client):
    r = client.get("/api/words")
    assert r.status_code == 200
    assert r.json["count"] == r.json["total"] == 10
    assert set(r.json["words"][0]) == {
        "slug", "term", "title", "category", "color", "tagline", "concepts", "projects"}


def test_search_by_term_concept_and_project(client):
    assert [w["slug"] for w in client.get("/api/words?q=psi").json["words"]] == ["mlops"]
    assert "rag" in [w["slug"] for w in client.get("/api/words?q=tf-idf").json["words"]]
    assert len(client.get("/api/words?q=sentinel").json["words"]) >= 1


def test_category_filter(client):
    r = client.get("/api/words?category=Architecture")
    assert r.json["count"] == 2
    assert {w["slug"] for w in r.json["words"]} == {"offline", "demo"}


@pytest.mark.parametrize("query", ["?limit=0", "?limit=abc", "?limit=-4"])
def test_bad_limit(client, query):
    assert client.get("/api/words" + query).status_code == 400


def test_limit(client):
    assert client.get("/api/words?limit=3").json["count"] == 3
    assert client.get("/api/words?limit=3").json["total"] == 10


def test_related(client):
    r = client.get("/api/words/risk/related")
    assert r.status_code == 200
    assert any(item["slug"] == "forecast" for item in r.json["related"])
    assert client.get("/api/words/nope/related").status_code == 404


def test_categories(client):
    r = client.get("/api/categories")
    assert r.status_code == 200
    assert sum(c["words"] for c in r.json["categories"]) == 10


def test_stats(client):
    r = client.get("/api/stats")
    assert r.status_code == 200
    assert r.json["words"] == 10
    assert r.json["projects"] == 8
    assert r.json["code_anchors"] >= 20
    assert r.json["palette"]["cyan"] == "#2DE7FF"


def test_cors_for_file_pages(client):
    r = client.get("/api/health")
    assert r.headers["Access-Control-Allow-Origin"] == "*"
    options = client.options("/api/words")
    assert options.headers["Access-Control-Allow-Methods"] == "GET, OPTIONS"


def test_unknown_route_is_json(client):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404
    assert r.json["ok"] is False


def test_root_is_a_small_directory(client):
    assert client.get("/").json["service"] == "word-atlas"

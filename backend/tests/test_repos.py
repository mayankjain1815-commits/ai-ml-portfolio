import pytest

from word_atlas.app import create_app, validate_data
from word_atlas.repos import REPOS, SNAPSHOT, get_repo, related_repos, repos_for_word
from word_atlas.themes import get_theme


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_validation_covers_repos_and_themes():
    assert validate_data() is True


def test_twenty_three_repos_in_the_orbit():
    assert len(REPOS) == 23
    assert len({r["slug"] for r in REPOS}) == 23
    assert len({r["name"] for r in REPOS}) == 23


def test_repo_list_shape_and_filters(client):
    r = client.get("/api/repos")
    assert r.status_code == 200
    assert r.json["count"] == r.json["total"] == 23
    assert r.json["snapshot"] == SNAPSHOT
    assert set(r.json["repos"][0]) >= {"slug", "name", "short", "stars", "language"}
    assert client.get("/api/repos?language=Python").json["count"] == sum(
        r["language"] == "Python" for r in REPOS)
    assert client.get("/api/repos?category=Security").json["count"] == sum(
        r["category"] == "Security" for r in REPOS)
    assert "omniroute" in [x["slug"] for x in client.get("/api/repos?q=proxy").json["repos"]]


def test_repo_sorting(client):
    stars = client.get("/api/repos?sort=stars").json["repos"]
    assert [x["stars"] for x in stars] == sorted([x["stars"] for x in stars], reverse=True)
    names = client.get("/api/repos?sort=name&limit=5").json["repos"]
    assert [x["name"] for x in names] == sorted(x["name"] for x in names)
    assert client.get("/api/repos?word=iot").json["count"] >= 2
    assert client.get("/api/repos?sort=bogus").status_code == 400
    assert client.get("/api/repos?limit=0").status_code == 400


@pytest.mark.parametrize("slug", [r["slug"] for r in REPOS])
def test_every_repo_has_a_full_record(client, slug):
    r = client.get(f"/api/repos/{slug}")
    assert r.status_code == 200
    record = r.json["repo"]
    assert record["slug"] == slug
    assert record["description"] and record["highlights"] and record["stack"]
    assert record["command"] and record["url"].startswith("https://github.com/")
    assert record["linked_words"]
    assert record["snapshot"] == SNAPSHOT


def test_unknown_repo_lists_available(client):
    r = client.get("/api/repos/missing")
    assert r.status_code == 404
    assert len(r.json["available"]) == 23
    assert client.get("/api/repos/missing/related").status_code == 404


def test_repo_related_and_word_reverse_links(client):
    rel = client.get("/api/repos/omniroute/related").json["related"]
    assert rel and all(x["slug"] != "omniroute" for x in rel)
    by_word = client.get("/api/words/iot/repos").json
    assert by_word["count"] >= 2
    assert "sentinel" in [r["slug"] for r in by_word["repos"]]
    assert client.get("/api/words/missing/repos").status_code == 404
    assert related_repos("missing") == []
    assert repos_for_word("missing") == []


def test_search_across_words_and_repos(client):
    r = client.get("/api/search?q=rag")
    assert r.status_code == 200
    kinds = {x["kind"] for x in r.json["results"]}
    assert "word" in kinds and "repo" in kinds
    assert client.get("/api/search?q=").json["count"] == 0
    assert client.get("/api/search?q=zenith&limit=2").json["count"] == 0
    assert client.get("/api/search?q=proxy&limit=2").json["count"] <= 2
    assert client.get("/api/search?q=rag&limit=abc").status_code == 400


def test_timeline_and_languages(client):
    timeline = client.get("/api/timeline").json["timeline"]
    assert len(timeline) == 23
    assert [x["updated"] for x in timeline] == sorted(
        [x["updated"] for x in timeline], reverse=True)
    langs = client.get("/api/languages").json
    assert langs["count"] == len({r["language"] for r in REPOS})
    assert sum(x["repos"] for x in langs["languages"]) == 23


def test_themes(client):
    r = client.get("/api/themes")
    assert r.status_code == 200
    assert {t["id"] for t in r.json["themes"]} == {"aurora"}
    aurora = client.get("/api/themes/aurora").json["theme"]
    assert aurora["snow"] is False
    assert aurora["colors"]["primary"].lower() == "#2de7ff"
    assert client.get("/api/themes/christmas").status_code == 404
    assert client.get("/api/themes/nope").status_code == 404
    assert get_theme("NOPE") is None


def test_stats_cover_the_solar_system(client):
    r = client.get("/api/stats").json
    assert r["words"] == 10
    assert r["repos"] == 23
    assert r["stars"] == sum(x["stars"] for x in REPOS)
    assert r["themes"] == 1
    assert set(r["theme_colors"]) == {"aurora"}
    assert r["bodies"] == 33
    assert r["moons"] >= 0


def test_word_detail_includes_repo_links(client):
    word = client.get("/api/words/rag").json["word"]
    assert word["repos"]
    assert all({"slug", "name", "short"} <= set(x) for x in word["repos"])


def test_repo_metadata_is_honest():
    assert get_repo("sih")["kind"] == "fork"
    assert get_repo("profile")["kind"] == "profile"
    assert all(r["url"].endswith(r["name"]) for r in REPOS)
    assert all(r["updated"].startswith("2026-") for r in REPOS)

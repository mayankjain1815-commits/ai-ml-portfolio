"""Flask API behind the landing page's solar-system atlas.

Read-only and fully offline. CORS is open because the page works straight from
disk (file://) as well as from a static host. Ten concept words are inner
planets; 23 public repositories are outer planets around one deterministic sun.
"""

from flask import Flask, jsonify, request

from . import __version__
from .data import PALETTE, REQUIRED_FIELDS, WORDS, all_words, get_word, related_words
from .repos import (
    REPO_REQUIRED_FIELDS, REPOS, SNAPSHOT, all_repos, get_repo,
    related_repos, repos_for_word,
)
from .themes import PALETTE as THEMES
from .themes import all_themes, get_theme
from .solar import (
    SOLAR_REQUIRED_FIELDS, all_bodies, get_body, neighbours, solar_payload,
    solar_stats,
)


def create_app():
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    @app.after_request
    def cors(response):
        # file:// pages send a null Origin; a wildcard is the only thing that works.
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/api/health")
    def health():
        return jsonify({
            "ok": True,
            "service": "word-atlas",
            "version": __version__,
            "words": len(WORDS),
            "repos": len(REPOS),
            "bodies": len(WORDS) + len(REPOS),
            "themes": len(THEMES),
            "snapshot": SNAPSHOT,
            "offline": True,
        })

    # ---------- concept words (inner planets) ----------

    @app.get("/api/words")
    def words():
        query = request.args.get("q", "").strip().lower()
        category = request.args.get("category", "").strip().lower()
        try:
            limit = int(request.args.get("limit", len(WORDS)))
        except ValueError:
            return jsonify({"ok": False, "error": "limit must be an integer"}), 400
        if limit < 1:
            return jsonify({"ok": False, "error": "limit must be positive"}), 400

        records = all_words()
        if query:
            records = [w for w in records if query in " ".join([
                w["term"], w["title"], w["tagline"], w["definition"],
                " ".join(w["concepts"]), " ".join(p["name"] for p in w["projects"]),
            ]).lower()]
        if category:
            records = [w for w in records if w["category"].lower() == category]

        return jsonify({
            "ok": True,
            "count": len(records[:limit]),
            "total": len(records),
            "words": [{
                "slug": w["slug"], "term": w["term"], "title": w["title"],
                "category": w["category"], "color": w["color"],
                "tagline": w["tagline"], "concepts": w["concepts"],
                "projects": [p["id"] for p in w["projects"]],
            } for w in records[:limit]],
        })

    @app.get("/api/words/<slug>")
    def word_detail(slug):
        word = get_word(slug)
        if word is None:
            return jsonify({
                "ok": False, "error": "unknown word", "slug": slug.lower(),
                "available": [w["slug"] for w in WORDS],
            }), 404
        word["related"] = related_words(slug)
        word["repos"] = [{
            "slug": r["slug"], "name": r["name"], "short": r["short"],
            "color": r["color"], "description": r["description"],
        } for r in repos_for_word(slug)]
        return jsonify({"ok": True, "word": word})

    @app.get("/api/words/<slug>/related")
    def word_related(slug):
        if get_word(slug) is None:
            return jsonify({"ok": False, "error": "unknown word"}), 404
        return jsonify({"ok": True, "slug": slug.lower(), "related": related_words(slug)})

    @app.get("/api/words/<slug>/repos")
    def word_repos(slug):
        if get_word(slug) is None:
            return jsonify({"ok": False, "error": "unknown word"}), 404
        records = repos_for_word(slug)
        return jsonify({"ok": True, "slug": slug.lower(), "count": len(records), "repos": records})

    @app.get("/api/categories")
    def categories():
        counts = {}
        for word in WORDS:
            counts[word["category"]] = counts.get(word["category"], 0) + 1
        return jsonify({
            "ok": True, "count": len(counts),
            "categories": [{"name": name, "words": count} for name, count in
                           sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))],
        })

    # ---------- repositories (outer planets) ----------

    @app.get("/api/repos")
    def repos():
        query = request.args.get("q", "").strip().lower()
        language = request.args.get("language", "").strip().lower()
        category = request.args.get("category", "").strip().lower()
        word = request.args.get("word", "").strip().lower()
        sort = request.args.get("sort", "name").strip().lower()
        try:
            limit = int(request.args.get("limit", len(REPOS)))
        except ValueError:
            return jsonify({"ok": False, "error": "limit must be an integer"}), 400
        if limit < 1:
            return jsonify({"ok": False, "error": "limit must be positive"}), 400
        if sort not in ("name", "stars", "updated", "language"):
            return jsonify({"ok": False, "error": "unknown sort"}), 400

        records = all_repos()
        if query:
            records = [r for r in records if query in " ".join([
                r["name"], r["description"], r["language"], r["category"],
                " ".join(r["stack"]), " ".join(r["highlights"]),
            ]).lower()]
        if language:
            records = [r for r in records if r["language"].lower() == language]
        if category:
            records = [r for r in records if r["category"].lower() == category]
        if word:
            records = [r for r in records if word in r["words"]]

        reverse = sort in ("stars", "updated")
        records.sort(key=lambda r: r[sort], reverse=reverse)
        return jsonify({
            "ok": True,
            "count": len(records[:limit]),
            "total": len(records),
            "snapshot": SNAPSHOT,
            "sort": sort,
            "repos": [{
                "slug": r["slug"], "name": r["name"], "short": r["short"],
                "description": r["description"], "language": r["language"],
                "stars": r["stars"], "updated": r["updated"], "url": r["url"],
                "category": r["category"], "color": r["color"],
                "words": r["words"], "kind": r["kind"],
            } for r in records[:limit]],
        })

    @app.get("/api/repos/<slug>")
    def repo_detail(slug):
        repo = get_repo(slug)
        if repo is None:
            return jsonify({
                "ok": False, "error": "unknown repository", "slug": slug.lower(),
                "available": [r["slug"] for r in REPOS],
            }), 404
        repo["related"] = related_repos(slug)
        repo["linked_words"] = [{
            "slug": w["slug"], "term": w["term"], "color": w["color"],
        } for w in WORDS if w["slug"] in repo["words"]]
        repo["snapshot"] = SNAPSHOT
        return jsonify({"ok": True, "repo": repo})

    @app.get("/api/repos/<slug>/related")
    def repo_related(slug):
        if get_repo(slug) is None:
            return jsonify({"ok": False, "error": "unknown repository"}), 404
        return jsonify({"ok": True, "slug": slug.lower(), "related": related_repos(slug)})

    @app.get("/api/languages")
    def languages():
        counts = {}
        for repo in REPOS:
            counts[repo["language"]] = counts.get(repo["language"], 0) + 1
        return jsonify({
            "ok": True, "count": len(counts),
            "languages": [{"name": name, "repos": count} for name, count in
                          sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))],
        })

    @app.get("/api/timeline")
    def timeline():
        records = sorted(REPOS, key=lambda r: r["updated"], reverse=True)
        return jsonify({
            "ok": True, "count": len(records), "snapshot": SNAPSHOT,
            "timeline": [{
                "slug": r["slug"], "name": r["name"], "updated": r["updated"],
                "category": r["category"], "color": r["color"],
            } for r in records],
        })

    # ---------- solar system ----------

    @app.get("/api/solar")
    def solar_system():
        return jsonify({"ok": True, **solar_payload()})

    @app.get("/api/solar/stats")
    def solar_summary():
        return jsonify({"ok": True, **solar_stats()})

    @app.get("/api/solar/<kind>/<slug>")
    def solar_body_detail(kind, slug):
        body = get_body(kind, slug)
        if body is None:
            return jsonify({
                "ok": False, "error": "unknown solar body",
                "kind": kind.lower(), "slug": slug.lower(),
                "available": [b["slug"] for b in all_bodies()
                              if b["kind"] == kind.lower().rstrip("s")],
            }), 404
        bodies = all_bodies()
        if body["kind"] == "word":
            record = get_word(slug)
            record["related"] = related_words(slug)
            record["repos"] = [{
                "slug": r["slug"], "name": r["name"], "short": r["short"],
                "color": r["color"], "description": r["description"],
            } for r in repos_for_word(slug)]
        else:
            record = get_repo(slug)
            record["related"] = related_repos(slug)
            record["linked_words"] = [{
                "slug": w["slug"], "term": w["term"], "color": w["color"],
            } for w in WORDS if w["slug"] in record["words"]]
            record["snapshot"] = SNAPSHOT
        return jsonify({
            "ok": True, "body": body, "record": record,
            "neighbours": neighbours(body, bodies),
            "note": "Orbital values are deterministic UI metadata, not astronomical facts.",
        })

    # ---------- search, themes and stats ----------

    @app.get("/api/search")
    def search():
        query = request.args.get("q", "").strip().lower()
        try:
            limit = int(request.args.get("limit", 12))
        except ValueError:
            return jsonify({"ok": False, "error": "limit must be an integer"}), 400
        if not query:
            return jsonify({"ok": True, "query": "", "count": 0, "results": []})
        results = []
        for word in WORDS:
            haystack = " ".join([
                word["term"], word["title"], word["tagline"], word["definition"],
                " ".join(word["concepts"]),
            ]).lower()
            if query in haystack:
                results.append({
                    "kind": "word", "slug": word["slug"], "label": word["term"],
                    "subtitle": word["title"], "color": word["color"],
                    "score": 3 if word["term"].lower().startswith(query) else 1,
                })
        for repo in REPOS:
            haystack = " ".join([
                repo["name"], repo["short"], repo["description"],
                repo["language"], repo["category"], " ".join(repo["stack"]),
                " ".join(repo["highlights"]),
            ]).lower()
            if query in haystack:
                results.append({
                    "kind": "repo", "slug": repo["slug"], "label": repo["name"],
                    "subtitle": f"{repo['language']} · {repo['category']}",
                    "color": repo["color"],
                    "score": 3 if repo["name"].lower().startswith(query) else 1,
                })
        results.sort(key=lambda r: (-r["score"], r["label"]))
        return jsonify({
            "ok": True, "query": query, "count": len(results[:limit]),
            "total": len(results), "results": results[:limit],
        })

    @app.get("/api/themes")
    def themes():
        return jsonify({"ok": True, "count": len(THEMES), "themes": all_themes()})

    @app.get("/api/themes/<theme_id>")
    def theme_detail(theme_id):
        theme = get_theme(theme_id)
        if theme is None:
            return jsonify({"ok": False, "error": "unknown theme"}), 404
        return jsonify({"ok": True, "theme": theme})

    @app.get("/api/stats")
    def stats():
        anchors = sum(len(w["code_anchors"]) for w in WORDS)
        steps = sum(len(w["how_it_works"]) for w in WORDS)
        pitfalls = sum(len(w["pitfalls"]) for w in WORDS)
        languages = {r["language"] for r in REPOS}
        categories = {r["category"] for r in REPOS}
        solar = solar_stats()
        return jsonify({
            "ok": True,
            "words": len(WORDS),
            "word_categories": len({w["category"] for w in WORDS}),
            "projects": len({p["id"] for w in WORDS for p in w["projects"]}),
            "code_anchors": anchors,
            "pipeline_steps": steps,
            "pitfalls": pitfalls,
            "repos": len(REPOS),
            "repo_categories": len(categories),
            "languages": len(languages),
            "stars": sum(r["stars"] for r in REPOS),
            "themes": len(THEMES),
            "bodies": solar["bodies"],
            "moons": solar["moons"],
            "ring_worlds": solar["ring_worlds"],
            "orbit_bands": solar["orbit_bands"],
            "snapshot": SNAPSHOT,
            "palette": PALETTE,
            "theme_colors": {t["id"]: t["colors"] for t in THEMES.values()},
        })

    @app.get("/")
    def index():
        return jsonify({
            "ok": True,
            "service": "word-atlas",
            "docs": [
                "/api/solar", "/api/solar/stats", "/api/solar/<kind>/<slug>",
                "/api/words", "/api/words/<slug>", "/api/words/<slug>/repos",
                "/api/repos", "/api/repos/<slug>", "/api/search",
                "/api/timeline", "/api/languages", "/api/themes", "/api/stats",
                "/api/health",
            ],
        })

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"ok": False, "error": "not found"}), 404

    return app


def validate_data():
    """Raise ValueError if any record is incomplete or reuses a slug."""
    for collection, fields, label in (
        (WORDS, REQUIRED_FIELDS, "word"),
        (REPOS, REPO_REQUIRED_FIELDS, "repo"),
        (all_bodies(), SOLAR_REQUIRED_FIELDS, "solar body"),
    ):
        seen = set()
        for record in collection:
            missing = [field for field in fields if field not in record]
            if missing:
                raise ValueError(f"{label} {record.get('slug', '?')} missing fields: {missing}")
            if record["slug"] in seen:
                raise ValueError(f"duplicate {label} slug: {record['slug']}")
            seen.add(record["slug"])
    for theme in all_themes():
        if not all(key in theme for key in ("id", "name", "colors", "snow", "ornaments")):
            raise ValueError(f"incomplete theme: {theme.get('id')}")
    return True

"""Flask API behind the landing page's rotating 3D words.

Every endpoint is read-only and fully offline. CORS is open because the page is
meant to work straight from disk (file://) as well as from a static host.
"""

from flask import Flask, jsonify, request

from . import __version__
from .data import PALETTE, REQUIRED_FIELDS, WORDS, all_words, get_word, related_words


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
            "offline": True,
        })

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
        return jsonify({"ok": True, "word": word})

    @app.get("/api/words/<slug>/related")
    def word_related(slug):
        if get_word(slug) is None:
            return jsonify({"ok": False, "error": "unknown word"}), 404
        return jsonify({"ok": True, "slug": slug.lower(), "related": related_words(slug)})

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

    @app.get("/api/stats")
    def stats():
        anchors = sum(len(w["code_anchors"]) for w in WORDS)
        steps = sum(len(w["how_it_works"]) for w in WORDS)
        pitfalls = sum(len(w["pitfalls"]) for w in WORDS)
        return jsonify({
            "ok": True,
            "words": len(WORDS),
            "categories": len({w["category"] for w in WORDS}),
            "projects": len({p["id"] for w in WORDS for p in w["projects"]}),
            "code_anchors": anchors,
            "pipeline_steps": steps,
            "pitfalls": pitfalls,
            "palette": PALETTE,
        })

    @app.get("/")
    def index():
        return jsonify({
            "ok": True,
            "service": "word-atlas",
            "docs": "/api/words, /api/words/<slug>, /api/categories, /api/stats, /api/health",
        })

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"ok": False, "error": "not found"}), 404

    return app


def validate_data():
    """Raise ValueError if any record is missing a field or reuses a slug."""
    seen = set()
    for word in WORDS:
        missing = [field for field in REQUIRED_FIELDS if field not in word]
        if missing:
            raise ValueError(f"{word.get('slug', '?')} missing fields: {missing}")
        if word["slug"] in seen:
            raise ValueError(f"duplicate slug: {word['slug']}")
        seen.add(word["slug"])
    return True

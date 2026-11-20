"""Flask dashboard for Sanket - India Disaster Intelligence Platform."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template

from .config import DEFAULT_RUNS, STATIC_DIR, TEMPLATES_DIR

app = Flask(
    __name__,
    static_folder=str(STATIC_DIR),
    static_url_path="/static",
    template_folder=str(TEMPLATES_DIR),
)
app.config["JSON_SORT_KEYS"] = False

logger = logging.getLogger("disaster_watch.dashboard")


def _load_json(path: Path):
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("could not read %s: %s", path.name, exc)
        return None


def load_run():
    return _load_json(DEFAULT_RUNS / "monitor.json")


@app.context_processor
def inject_now():
    return {"now_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")}


@app.route("/")
def index():
    summary = load_run()
    context = {"has_run": summary is not None}
    if summary is not None:
        context.update(summary)
    return render_template("index.html", **context)


@app.route("/india-map")
def india_map():
    summary = load_run()
    context = {"has_run": summary is not None}
    if summary is not None:
        context.update(summary)
    return render_template("india_map.html", **context)


@app.route("/alerts-center")
def alerts_center():
    summary = load_run()
    context = {"has_run": summary is not None}
    if summary is not None:
        context.update(summary)
    return render_template("alerts.html", **context)


@app.route("/incidents")
def incidents():
    summary = load_run()
    context = {"has_run": summary is not None}
    if summary is not None:
        context.update(summary)
    return render_template("incidents.html", **context)


@app.route("/forecasts")
def forecasts():
    summary = load_run()
    context = {"has_run": summary is not None}
    if summary is not None:
        context.update(summary)
    return render_template("forecasts.html", **context)


@app.route("/sensors")
def sensors():
    summary = load_run()
    context = {"has_run": summary is not None}
    if summary is not None:
        context.update(summary)
    return render_template("sensors.html", **context)


@app.route("/subdivisions")
def subdivisions():
    summary = load_run()
    context = {"has_run": summary is not None}
    if summary is not None:
        context.update(summary)
    return render_template("subdivisions.html", **context)


@app.route("/reports")
def reports():
    summary = load_run()
    context = {"has_run": summary is not None}
    if summary is not None:
        context.update(summary)
    return render_template("reports.html", **context)


@app.route("/api-docs")
def api_docs():
    summary = load_run()
    context = {"has_run": summary is not None}
    if summary is not None:
        context.update(summary)
    return render_template("api_docs.html", **context)


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/about")
def about():
    summary = load_run()
    context = {"has_run": summary is not None}
    if summary is not None:
        context.update(summary)
    return render_template("about.html", **context)


@app.route("/api/overview")
def api_overview():
    summary = load_run()
    if summary is None:
        return jsonify({"error": "no run yet"}), 404
    return jsonify({
        "generated_at": summary.get("generated_at"),
        "alert_count": summary.get("alert_count"),
        "affected_count": summary.get("affected_count"),
        "areas_monitored": summary.get("areas_monitored") or len(summary.get("current_weather") or []),
    })


@app.route("/api/weather")
def api_weather():
    summary = load_run()
    if summary is None:
        return jsonify({"error": "no run yet"}), 404
    return jsonify({"current_weather": summary.get("current_weather") or []})


@app.route("/api/risk")
def api_risk():
    summary = load_run()
    if summary is None:
        return jsonify({"error": "no run yet"}), 404
    return jsonify({"disaster_risk": summary.get("disaster_risk") or []})


@app.route("/api/alerts")
def api_alerts():
    summary = load_run()
    if summary is None:
        return jsonify({"error": "no run yet"}), 404
    return jsonify({"active_alerts": summary.get("active_alerts") or []})


@app.route("/api/affected")
def api_affected():
    summary = load_run()
    if summary is None:
        return jsonify({"error": "no run yet"}), 404
    return jsonify({"affected_areas": summary.get("affected_areas") or []})


@app.route("/api/incidents")
def api_incidents():
    summary = load_run()
    if summary is None:
        return jsonify({"error": "no run yet"}), 404
    return jsonify({"recent_incidents": summary.get("recent_incidents") or []})


@app.route("/api/forecast")
def api_forecast():
    summary = load_run()
    if summary is None:
        return jsonify({"error": "no run yet"}), 404
    path = DEFAULT_RUNS / "forecast.json"
    if path.exists():
        return jsonify(json.loads(path.read_text()))
    return jsonify({"forecast": []})


@app.route("/api/sensors")
def api_sensors():
    return jsonify({
        "sensors": {
            "aws": {"total": 2847, "online": 2810},
            "rain_gauges": {"total": 1432, "online": 1402},
            "river_gauges": {"total": 901, "online": 893},
            "radars": {"total": 37, "online": 37},
        }
    })


@app.route("/api/system/health")
def api_system_health():
    summary = load_run()
    return jsonify({
        "status": "operational",
        "has_data": summary is not None,
        "scope": "india",
        "granularity": ["state", "district", "subdivision", "block", "village", "ward"],
    })


def serve(host: str = "127.0.0.1", port: int = 5107) -> None:
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    serve()

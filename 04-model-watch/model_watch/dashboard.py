"""Flask dashboard: the human-facing window into a monitoring run.

No CDN, no JS framework, no network — a server-rendered single page plus a few
matplotlib PNGs generated on demand into ``static/``. The JSON endpoints
(``/api/metrics``, ``/api/drift``, ``/api/alerts``) exist so the same run data
can feed whatever frontend a real team wants later.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless backend; charts are written to disk, not shown
import matplotlib.pyplot as plt  # noqa: E402

import pandas as pd  # noqa: E402
from flask import Flask, jsonify, render_template  # noqa: E402

from model_watch.data_gen import FEATURES, generate  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = PROJECT_ROOT / "runs" / "latest"
STATIC_DIR = PROJECT_ROOT / "static"

app = Flask(
    __name__,
    static_folder=str(STATIC_DIR),
    static_url_path="/static",
    template_folder=str(Path(__file__).resolve().parent / "templates"),
)
app.config["JSON_SORT_KEYS"] = False

logger = logging.getLogger("model_watch.dashboard")


# ---------------------------------------------------------------------------
# run data loading
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("could not read %s: %s", path.name, exc)
        return None


def load_run() -> dict | None:
    """The latest monitoring run, or ``None`` when nothing has run yet."""
    summary = _load_json(RUNS_DIR / "monitor.json")
    if summary is None:
        return None
    alerts = _load_json(RUNS_DIR / "alerts.json") or {"alerts": []}
    summary = dict(summary)
    summary.setdefault("alerts", alerts["alerts"])
    return summary


def _reference_frame(summary: dict) -> pd.DataFrame:
    seed = (summary.get("reference") or {}).get("dataset_seed")
    n_rows = (summary.get("reference") or {}).get("n_rows") or 12_000
    return generate(n_rows, seed=int(seed or 42)).frame


def _severity_color(severity: str) -> str:
    return {"ok": "#2e7d32", "warn": "#f9a825", "alert": "#c62828"}.get(severity, "#455a64")


# ---------------------------------------------------------------------------
# charts (regenerated only when the run is newer than the PNG)
# ---------------------------------------------------------------------------

_CHARTS = ("psi_bar.png", "accuracy_trend.png", "feature_dist.png")


def charts_stale(summary: dict) -> bool:
    run_mtime = (RUNS_DIR / "monitor.json").stat().st_mtime
    return any(
        not (STATIC_DIR / name).exists() or (STATIC_DIR / name).stat().st_mtime < run_mtime
        for name in _CHARTS
    )


def render_charts(summary: dict) -> None:
    """(Re)draw the three dashboard PNGs into ``static/``."""
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    # 1 — per-feature PSI on the latest day, colored by severity.
    features = summary.get("features") or {}
    names = list(features)
    values = [features[n]["psi"] for n in names]
    colors = [_severity_color(features[n]["severity"]) for n in names]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.bar(names, values, color=colors)
    ax.axhline(0.10, color="#f9a825", linestyle="--", linewidth=1, label="warn ≥ 0.10")
    ax.axhline(0.25, color="#c62828", linestyle="--", linewidth=1, label="alert ≥ 0.25")
    ax.set_ylabel("PSI (latest day)")
    ax.set_title("Per-feature population stability index")
    ax.tick_params(axis="x", rotation=45)
    ax.legend()
    fig.tight_layout()
    fig.savefig(STATIC_DIR / "psi_bar.png", dpi=110)
    plt.close(fig)

    # 2 — live accuracy/F1 over the 60 days with phase shading.
    trend = summary.get("trend_points") or []
    if trend:
        days = [p["day"] for p in trend]
        fig, ax = plt.subplots(figsize=(9, 3.6))
        ax.plot(days, [p["accuracy"] for p in trend], marker=".", label="accuracy")
        ax.plot(days, [p["f1"] for p in trend], marker=".", label="f1")
        for phase, (start, end) in (summary.get("phases") or {}).items():
            if start >= end:
                continue
            color = {"normal": "#e8f5e9", "covariate_drift": "#fff8e1", "concept_drift": "#fdecea"}[phase]
            ax.axvspan(start, end, color=color)
        ax.set_xlabel("production day")
        ax.set_ylabel("score")
        ax.set_title("Live accuracy & F1 (labels arrive 2 days late)")
        ax.set_ylim(0.4, 1.0)
        ax.legend(loc="lower left")
        fig.tight_layout()
        fig.savefig(STATIC_DIR / "accuracy_trend.png", dpi=110)
        plt.close(fig)

    # 3 — reference vs current distribution, one panel per feature.
    current = pd.read_csv(RUNS_DIR / "current_features.csv")
    reference = _reference_frame(summary)[FEATURES]
    fig, axes = plt.subplots(3, 3, figsize=(12, 8))
    for ax, feature in zip(axes.ravel(), FEATURES):
        ax.hist(reference[feature], bins=30, density=True, alpha=0.55,
                color="#90a4ae", label="train")
        ax.hist(current[feature], bins=30, density=True, alpha=0.65,
                color="#1e88e5", label="current")
        ax.set_title(feature, fontsize=9)
        ax.tick_params(labelsize=7)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Feature distribution: training population vs current batch")
    fig.tight_layout()
    fig.savefig(STATIC_DIR / "feature_dist.png", dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------------------
# routes
# ---------------------------------------------------------------------------

@app.route("/")
def index() -> str:
    summary = load_run()
    context: dict = {
        "has_run": summary is not None,
        "charts": _CHARTS,
        "features": FEATURES,
        "psi_warn": 0.10,
        "psi_alert": 0.25,
    }
    if summary is not None:
        if charts_stale(summary):
            try:
                render_charts(summary)
            except Exception:  # a broken chart must not take the page down
                logger.exception("chart generation failed")
        context.update(
            alert_summary=summary.get("alert_summary") or {},
            model=summary.get("model") or {},
            live=summary.get("performance") or {},
            features=summary.get("features") or {},
            alerts=(summary.get("alerts") or [])[:25],
            days=summary.get("days"),
            label_delay=summary.get("label_delay"),
            trend_points=summary.get("trend_points") or [],
            phases=summary.get("phases") or {},
            stream=summary.get("stream") or {},
            severity_color=_severity_color,
            psi_warn=0.10,
            psi_alert=0.25,
        )
    return render_template("index.html", **context)


@app.route("/api/metrics")
def api_metrics():
    summary = load_run()
    if summary is None:
        return jsonify({"error": "no run yet — run `python -m model_watch demo` first"}), 404
    return jsonify(
        {
            "model": summary.get("model"),
            "live": summary.get("performance"),
            "days": summary.get("days"),
            "label_delay": summary.get("label_delay"),
            "alert_summary": summary.get("alert_summary"),
            "trend_window": summary.get("trend_window"),
        }
    )


@app.route("/api/drift")
def api_drift():
    summary = load_run()
    if summary is None:
        return jsonify({"error": "no run yet — run `python -m model_watch demo` first"}), 404
    feature_drift = summary.get("features") or {}
    daily = [
        {"day": d["day"], "phase": d["phase"], "psi_mean": d["psi_mean"]}
        for d in summary.get("daily") or []
    ]
    return jsonify(
        {
            "features": feature_drift,
            "daily_psi": daily,
            "phases": summary.get("phases"),
            "thresholds": {"psi_stable": 0.10, "psi_warn": 0.25},
        }
    )


@app.route("/api/alerts")
def api_alerts():
    summary = load_run()
    if summary is None:
        return jsonify({"error": "no run yet — run `python -m model_watch demo` first"}), 404
    return jsonify({"alerts": summary.get("alerts") or []})


def serve(host: str = "127.0.0.1", port: int = 5104) -> None:
    """Start the dashboard (no reloader: it is a read-only report view)."""
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    serve()
"""End-to-end tests: the monitoring loop, report rendering, and the dashboard API.

These exercise the *whole* pipeline the CLI runs (stream → monitor → drift →
alerts → persistence) against a small deterministic run in ``tmp_path``, plus
the pure report renderer and the Flask API with a stubbed run directory.
"""

import json

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from model_watch.data_gen import FEATURES, TARGET, generate
from model_watch.monitor import Monitor, render_report, run_monitoring
from model_watch.stream import Batch, StreamSimulator


def _tiny_model():
    ds = generate(1_200, seed=3)
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, random_state=3))
    model.fit(ds.x, ds.y)
    return model


def test_run_monitoring_small_run(tmp_path):
    model = _tiny_model()
    manifest = {
        "version": 1,
        "algorithm": "logistic_regression",
        "hyperparams": {"max_iter": 500},
        "metrics": {"accuracy": 0.75, "f1": 0.6, "roc_auc": 0.8},
        "created_at": "2026-01-01T00:00:00+00:00",
        "dataset_seed": 3,
        "n_rows": 1_200,
    }
    reference = generate(1_200, seed=3).frame

    summary = run_monitoring(
        model=model,
        manifest=manifest,
        reference=reference,
        days=12,
        batch_size=150,
        seed=11,
        out_dir=tmp_path / "run",
    )

    # the run produced the documented artifacts
    assert (tmp_path / "run" / "monitor.json").exists()
    assert (tmp_path / "run" / "alerts.json").exists()
    assert (tmp_path / "run" / "alerts.log").exists()
    assert (tmp_path / "run" / "current_features.csv").exists()

    # summary carries the full arc: all three phases observed across 12 days
    assert summary["days"] == 12
    phases = summary["phases"]
    assert phases["normal"][0] == 1
    assert phases.get("covariate_drift") and phases.get("concept_drift")

    # every feature got a drift measurement and a severity label
    assert set(summary["features"]) == set(FEATURES)
    assert all(state["severity"] in ("ok", "warn", "alert") for state in summary["features"].values())

    # concept-drift trend collected once labels matured past the 2-day delay
    points = summary["trend_points"]
    assert points and points[-1]["day"] == 12
    assert {"accuracy", "f1"} <= set(points[-1])

    # model + stream provenance made it into the report payload
    assert summary["model"]["version"] == 1
    assert summary["stream"]["seed"] == 11

    # the report renders out of the saved summary without error
    text = render_report(summary)
    assert "MODEL WATCH" in text
    assert "normal" in text and "concept_drift" in text
    assert "tenure_months" in text


def test_run_monitoring_correctly_detects_alert_phase(tmp_path):
    """The 3-phase stream is engineered to drift; the monitor must notice."""
    model = _tiny_model()
    manifest = {"version": 1, "dataset_seed": 3, "n_rows": 1_200}
    reference = generate(1_200, seed=3).frame

    summary = run_monitoring(
        model=model,
        manifest=manifest,
        reference=reference,
        days=20,
        batch_size=150,
        seed=5,
        out_dir=tmp_path / "run",
    )

    # the drift is real: PSI on a drifting feature crosses the warning band
    worst_psi = max(state["psi"] for state in summary["features"].values())
    assert worst_psi > 0.10
    # and the alert manager recorded something non-trivial
    assert sum(summary["alert_summary"].values()) >= 1


def test_stream_phases_and_magnitude_ramp():
    sim = StreamSimulator(days=12, batch_size=50, seed=1)
    batches = list(sim)
    assert len(batches) == 12
    assert batches[0].phase == "normal"
    assert batches[0].day == 1
    # phases scale with the run length at 60-day proportions
    assert batches[0].phase == "normal"          # day 1 < covariate_start
    assert batches[-1].phase == "concept_drift"
    # magnitude ramps from 0 during covariate drift
    cov = [b for b in batches if b.phase == "covariate_drift"]
    assert cov, "expected a covariate-drift window in a 12-day run"
    mags = [sim._magnitude(b.day) for b in cov]
    assert mags[0] < mags[-1]


def test_monitor_requires_reference_features(tmp_path):
    from model_watch import alerts

    bad = pd.DataFrame({"not_a_feature": [1.0, 2.0]})
    alerts_mgr = alerts.AlertManager(
        log_path=tmp_path / "a.log", json_path=tmp_path / "a.json"
    )
    with pytest.raises(ValueError):
        Monitor(model=_tiny_model(), reference=bad, alerts=alerts_mgr)


def test_dashboard_api_serves_run(tmp_path, monkeypatch):
    import model_watch.dashboard as dashboard
    from model_watch.dashboard import app

    # stub the run directory with a minimal-but-valid run payload
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    payload = {
        "days": 12,
        "label_delay": 2,
        "features": {f: {"psi": 0.05, "ks": 0.1, "severity": "ok"} for f in FEATURES[:3]},
        "phases": {"normal": [1, 3], "covariate_drift": [4, 8], "concept_drift": [9, 12]},
        "trend_points": [{"day": d, "accuracy": 0.8, "f1": 0.7, "phase": "normal"} for d in range(3, 13)],
        "performance": {"accuracy": 0.8, "precision": 0.7, "recall": 0.7, "f1": 0.7},
        "model": {"version": 1, "algorithm": "logistic_regression"},
        "alert_summary": {"ok": 0, "warn": 1, "alert": 0},
        "alerts": [],
        "reference": {"dataset_seed": 3, "n_rows": 1_200},
    }
    (run_dir / "monitor.json").write_text(json.dumps(payload))
    (run_dir / "alerts.json").write_text(json.dumps({"alerts": []}))

    monkeypatch.setattr(dashboard, "RUNS_DIR", run_dir)
    client = app.test_client()
    assert client.get("/api/metrics").status_code == 200
    assert client.get("/api/drift").status_code == 200
    assert client.get("/api/alerts").status_code == 200

    body = client.get("/api/metrics").get_json()
    assert body["model"]["version"] == 1
    assert body["days"] == 12


def test_dashboard_api_404_without_run(tmp_path, monkeypatch):
    import model_watch.dashboard as dashboard
    from model_watch.dashboard import app

    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(dashboard, "RUNS_DIR", empty)
    client = app.test_client()
    assert client.get("/api/metrics").status_code == 404
    assert client.get("/api/drift").status_code == 404
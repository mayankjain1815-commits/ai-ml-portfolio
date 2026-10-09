import numpy as np
import pickle
from datetime import datetime, timezone
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from model_watch import drift, metrics
from model_watch.data_gen import FEATURES, generate, reference_stats, shift
from model_watch import alerts
from model_watch.registry import ModelRegistry


class DummyModel:
    """Module-level so the registry can pickle it (locals can't be pickled)."""

    def predict(self, X):
        return np.zeros(len(X))

    def predict_proba(self, X):
        return np.column_stack([np.zeros(len(X)), np.ones(len(X))])


def test_metrics_vs_sklearn_toy():
    y_true = [0, 0, 1, 1, 0, 1, 1, 0, 1]
    y_pred = [0, 0, 1, 0, 0, 1, 0, 0, 1]
    y_score = [0.1, 0.2, 0.8, 0.4, 0.3, 0.9, 0.5, 0.2, 0.8]

    assert np.isclose(metrics.accuracy(y_true, y_pred), accuracy_score(y_true, y_pred), atol=1e-12)
    assert np.isclose(metrics.precision(y_true, y_pred), precision_score(y_true, y_pred, zero_division=0), atol=1e-12)
    assert np.isclose(metrics.recall(y_true, y_pred), recall_score(y_true, y_pred, zero_division=0), atol=1e-12)
    assert np.isclose(metrics.f1(y_true, y_pred), f1_score(y_true, y_pred, zero_division=0), atol=1e-12)
    assert np.isclose(metrics.roc_auc(y_true, y_score), roc_auc_score(y_true, y_score), atol=1e-12)


def test_confusion_counts():
    tp, fp, tn, fn = metrics.confusion_counts([0, 0, 1], [0, 1, 1])
    assert (tp, fp, tn, fn) == (1, 1, 1, 0)


def test_generate_seeded_determinism():
    d1 = generate(100, seed=13).frame
    d2 = generate(100, seed=13).frame
    assert d1.equals(d2)
    # different seed gives different values
    assert not generate(100, seed=14).frame.equals(d1)


def test_ps_identical_distributions_zero():
    rng = np.random.default_rng(123)
    a = rng.normal(0, 1, 5000)
    b = rng.normal(0, 1, 5000)
    assert drift.psi(a, b) < 1e-2
    # identical -> 0
    c = np.array([0.1, 0.2, 0.3, 0.4])
    assert drift.psi(c, c) == 0.0


def test_psi_grows_with_shift():
    rng = np.random.default_rng(99)
    ref = rng.normal(0, 1, 8000)
    small = rng.normal(0.15, 1, 8000)
    large = rng.normal(0.6, 1, 8000)
    p_small = drift.psi(ref, small)
    p_large = drift.psi(ref, large)
    assert p_small < p_large
    assert p_large > 0.25


def test_psi_degenerate_constant_feature():
    # single constant value on both sides -> no measurable drift
    assert drift.psi([3.0, 3.0, 3.0], [3.0, 3.0, 3.0]) == 0.0
    # constant expected but shifted actual -> infinite distance
    assert drift.psi([1.0, 1.0, 1.0], [5.0, 5.0, 5.0]) == float("inf")


def test_shift_is_parametrized_and_monotonic():
    ds = generate(500, seed=5)
    ref_stats = reference_stats(ds.x)
    f0 = shift(ds.x.copy(), magnitude=0.0, stats=ref_stats)
    assert f0.equals(ds.x[FEATURES])

    f1 = shift(ds.x.copy(), magnitude=0.3, stats=ref_stats)
    f2 = shift(ds.x.copy(), magnitude=0.6, stats=ref_stats)
    f1p = shift(ds.x.copy(), magnitude=0.3, stats=ref_stats)
    # determinism
    assert f1.equals(f1p)
    # magnitude matters
    assert drift.psi(ds.x["tenure_months"], f1["tenure_months"]) < drift.psi(ds.x["tenure_months"], f2["tenure_months"])


def test_ks_statistic_toy_samples():
    # same distribution -> 0
    assert np.isclose(drift.ks_statistic([1, 2, 3, 4], [1, 2, 3, 4]), 0.0, atol=1e-12)
    # completely separated -> 1
    assert np.isclose(drift.ks_statistic([0, 0.1], [0.9, 1.0]), 1.0, atol=1e-12)
    # known value
    assert np.isclose(drift.ks_statistic([1, 2, 3, 4, 5], [1, 3, 5, 7, 9]), 0.4, atol=1e-12)


def test_ks_computable_on_feature():
    ds = generate(2000, seed=7)
    x = ds.x["tenure_months"].to_numpy()
    y = x + 1.0
    assert 0.01 < drift.ks_statistic(x, y) < 0.05


def test_registry_roundtrip(tmp_path):
    reg = ModelRegistry(tmp_path)
    v = reg.register(
        model=DummyModel(),
        algorithm="dummy",
        hyperparams={"a": 1},
        metrics={"accuracy": 0.5, "f1": 0.4, "roc_auc": 0.6, "precision": 0.5, "recall": 0.5},
        dataset_hash="deadbeef",
        feature_names=list(FEATURES),
        dataset_seed=1,
        n_rows=100,
    )
    model, entry = reg.load(v)
    assert entry["version"] == v
    assert entry["metrics"]["roc_auc"] == 0.6
    assert entry["dataset_seed"] == 1
    assert entry["n_rows"] == 100
    path = reg.model_path(v)
    assert path.exists()
    with path.open("rb") as f:
        loaded = pickle.load(f)
    assert hasattr(loaded, "predict")
    # versions monotonically increase and manifest is persisted
    v2 = reg.register(
        model=DummyModel(),
        algorithm="dummy",
        hyperparams={"a": 2},
        metrics={"accuracy": 0.6},
        dataset_hash="cafebabe",
        feature_names=list(FEATURES),
    )
    assert v2 == v + 1
    assert len(reg.list_versions()) == 2


def _alert_manager(tmp_path, window_hours=24.0):
    time = {"t": datetime(2026, 4, 1, tzinfo=timezone.utc)}
    mgr = alerts.AlertManager(
        log_path=tmp_path / "alerts.log",
        json_path=tmp_path / "alerts.json",
        window_hours=window_hours,
        clock=lambda: time["t"],
    )
    return mgr, time


def test_alert_dedup_within_window(tmp_path):
    mgr, time = _alert_manager(tmp_path)
    det = drift.Detection.now("tenure_months", "psi", 0.32, "alert")

    mgr.raise_event(det)  # t0 -> new record
    recs = mgr.records()
    assert len(recs) == 1 and recs[0].count == 1

    # same feature+severity within the window -> dedup, count rises, no new record
    time["t"] = datetime(2026, 4, 1, 23, tzinfo=timezone.utc)
    mgr.raise_event(det)
    recs = mgr.records()
    assert len(recs) == 1 and recs[0].count == 2

    # window is rolling on last_seen: 12h after the 23h event is still inside
    time["t"] = datetime(2026, 4, 2, 11, tzinfo=timezone.utc)
    mgr.raise_event(det)
    recs = mgr.records()
    assert len(recs) == 1 and recs[0].count == 3

    # a different feature is its own record
    det2 = drift.Detection.now("monthly_charges", "ksi", 0.4, "alert")
    mgr.raise_event(det2)
    recs = mgr.records()
    assert len(recs) == 2
    assert {r.feature for r in recs} == {"tenure_months", "monthly_charges"}


def test_alert_fresh_record_after_window(tmp_path):
    mgr, time = _alert_manager(tmp_path)
    det = drift.Detection.now("tenure_months", "psi", 0.32, "alert")
    mgr.raise_event(det)
    time["t"] = datetime(2026, 4, 1, 23, tzinfo=timezone.utc)
    mgr.raise_event(det)
    assert mgr.records()[0].count == 2

    # well past the 24h window -> this is a NEW occurrence: pages again, count resets
    time["t"] = datetime(2026, 4, 5, tzinfo=timezone.utc)
    mgr.raise_event(det)
    recs = mgr.records()
    assert len(recs) == 1  # same key, but a fresh record replaced the old one
    assert recs[0].count == 1
    assert recs[0].first_seen == recs[0].last_seen


def test_alert_escalation_is_new_record(tmp_path):
    mgr, time = _alert_manager(tmp_path)
    mgr.raise_event(drift.Detection.now("tenure_months", "psi", 0.20, "warn"))
    mgr.raise_event(drift.Detection.now("tenure_months", "psi", 0.32, "alert"))
    recs = mgr.records()
    assert len(recs) == 2
    assert {r.severity for r in recs} == {"warn", "alert"}


def test_alert_ok_ignored(tmp_path):
    mgr, time = _alert_manager(tmp_path)
    assert mgr.raise_event(drift.Detection.now("tenure_months", "psi", 0.05, "ok")) is None
    assert mgr.records() == []


def test_alert_persistence_roundtrip(tmp_path):
    mgr, time = _alert_manager(tmp_path)
    mgr.raise_event(drift.Detection.now("tenure_months", "psi", 0.32, "alert"))
    # a fresh manager over the same files reloads the record
    reloaded = alerts.AlertManager(
        log_path=tmp_path / "alerts.log",
        json_path=tmp_path / "alerts.json",
        window_hours=24.0,
        clock=lambda: time["t"],
    )
    recs = reloaded.records()
    assert len(recs) == 1
    assert recs[0].feature == "tenure_months"
    assert recs[0].count == 1
    # the human-readable log got the chronological line
    log_text = (tmp_path / "alerts.log").read_text()
    assert "tenure_months" in log_text and "[ALERT]" in log_text


def test_summary_counts_by_severity(tmp_path):
    mgr, time = _alert_manager(tmp_path)
    mgr.raise_event(drift.Detection.now("a", "psi", 0.12, "warn"))
    mgr.raise_event(drift.Detection.now("b", "psi", 0.4, "alert"))
    mgr.raise_event(drift.Detection.now("c", "psi", 0.3, "alert"))
    assert mgr.summary() == {"ok": 0, "warn": 1, "alert": 2}


def test_trend_slope_alert():
    # clearly declining accuracy over 14 days: go from 0.8 down to 0.6
    series = {i: 0.8 - (i - 1) * 0.015 for i in range(1, 15)}
    sev, slope, n = drift.trend_severity(series, window=14, slope_warn=-0.002, slope_alert=-0.005)
    assert sev in ("warn", "alert")
    assert slope < -0.005
    assert n == 14


def test_metrics_hand_equal_sklearn_on_random():
    rng = np.random.default_rng(42)
    for _ in range(20):
        y_true = rng.integers(0, 2, size=50)
        y_pred = rng.integers(0, 2, size=50)
        y_score = rng.random(50)
        assert np.isclose(metrics.accuracy(y_true, y_pred), accuracy_score(y_true, y_pred), atol=1e-12)
        assert np.isclose(metrics.f1(y_true, y_pred), f1_score(y_true, y_pred, zero_division=0), atol=1e-9)
        assert np.isclose(metrics.precision(y_true, y_pred), precision_score(y_true, y_pred, zero_division=0), atol=1e-12)
        assert np.isclose(metrics.recall(y_true, y_pred), recall_score(y_true, y_pred, zero_division=0), atol=1e-12)
        # need both classes
        if y_true.sum() in (0, 50):
            continue
        assert np.isclose(metrics.roc_auc(y_true, y_score), roc_auc_score(y_true, y_score), atol=1e-12)
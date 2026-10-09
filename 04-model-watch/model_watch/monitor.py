"""The monitoring loop: scores traffic, measures drift, pages when things move.

A model monitor is a pipeline that runs *after* the model:

    predict → stash prediction (labels are late) → measure feature drift →
    when labels arrive, measure performance → trend the performance →
    escalate severe drift to the alert manager → persist everything for the
    dashboard/report.

:class:`Monitor` owns that loop; :func:`run_monitoring` is the one-call entry
point that wire it to a stream, a registry manifest and a run directory.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from model_watch.alerts import AlertManager
from model_watch.data_gen import FEATURES, TARGET, reference_stats
from model_watch.drift import (
    Detection,
    KS_ALERT,
    KS_WARN,
    PSI_STABLE,
    PSI_WARN,
    SLOPE_ALERT,
    SLOPE_WARN,
    classify,
    ks_statistic,
    psi,
    trend_severity,
)
from model_watch.metrics import binary_metrics
from model_watch.stream import Batch, StreamSimulator

logger = logging.getLogger("model_watch.monitor")

BASE_DAY = date(2026, 3, 1)


def _stamp_for_day(day: int) -> str:
    """Simulated production timestamp: the demo replays 60 days of "real" time."""
    return datetime.combine(BASE_DAY + timedelta(days=day - 1), datetime.min.time(), tzinfo=timezone.utc).isoformat()


@dataclass
class _PendingLabel:
    """Prediction held until the ground truth for its day becomes known."""

    day: int
    predictions: np.ndarray
    actuals: np.ndarray
    phase: str
    evaluated: bool = False


class Monitor:
    """Ingests :class:`Batch` objects and accumulates monitoring evidence."""

    def __init__(
        self,
        model: Any,
        reference: pd.DataFrame,
        *,
        label_delay_days: int = 2,
        trend_window: int = 14,
        confirm_evals: int = 2,
        psi_stable: float = PSI_STABLE,
        psi_warn: float = PSI_WARN,
        ks_warn: float = KS_WARN,
        ks_alert: float = KS_ALERT,
        slope_warn: float = SLOPE_WARN,
        slope_alert: float = SLOPE_ALERT,
        alerts: AlertManager,
    ) -> None:
        self.model = model
        self.reference = reference
        if set(FEATURES) - set(reference.columns):
            raise ValueError("reference frame is missing model features")
        self.label_delay = label_delay_days
        self.trend_window = trend_window
        # A trend slope must stay past its threshold for this many consecutive
        # *evaluations* before we page — batch-level accuracy is noisy, and a
        # one-day dip is not an outage. Sustained degradation is.
        self.confirm_evals = confirm_evals
        self.psi_warn, self.psi_stable = psi_warn, psi_stable
        self.ks_warn, self.ks_alert = ks_warn, ks_alert
        self.slope_warn, self.slope_alert = slope_warn, slope_alert
        self.alerts = alerts

        self._reference_stats = reference_stats(reference[FEATURES])
        self._reference_values = {f: reference[f].to_numpy(dtype=float) for f in FEATURES}
        self._pending: list[_PendingLabel] = []
        self._daily: list[dict[str, Any]] = []
        self._detections: list[dict[str, Any]] = []
        self._trend: dict[int, dict[str, float]] = {}
        self._feature_state: dict[str, dict[str, Any]] = {}
        self._concept_streak: tuple[Severity, int] = ("ok", 0)
        self._current_features: pd.DataFrame | None = None
        self._last_day: int | None = None

    # -- per-batch pipeline ---------------------------------------------------

    def observe(self, batch: Batch) -> None:
        """Score one batch and measure everything measurable *today*."""
        self._last_day = batch.day
        self._current_features = batch.features

        proba = self.model.predict_proba(batch.features[FEATURES])[:, 1]
        predictions = (proba >= 0.5).astype(int)
        self._pending.append(
            _PendingLabel(
                day=batch.day,
                predictions=predictions,
                actuals=batch.target.to_numpy(dtype=int),
                phase=batch.phase,
            )
        )

        self._measure_feature_drift(batch)
        self._evaluate_matured_labels(batch.day, batch.phase)

    def finish(self) -> dict[str, Any]:
        """Flush remaining pending labels (labels always arrive eventually)."""
        for pending in self._pending:
            if not pending.evaluated:
                self._evaluate(pending)
        return self.summary()

    # -- drift measurement ----------------------------------------------------

    def _measure_feature_drift(self, batch: Batch) -> None:
        row: dict[str, Any] = {"day": batch.day, "phase": batch.phase, "psi": {}, "ks": {}}
        for feature in FEATURES:
            current = batch.features[feature].to_numpy(dtype=float)
            ref = self._reference_values[feature]

            psi_value = psi(ref, current)
            ks_value = ks_statistic(ref, current)
            row["psi"][feature] = psi_value
            row["ks"][feature] = ks_value

            psi_sev = classify(psi_value, self.psi_stable, self.psi_warn)
            ks_sev = classify(ks_value, self.ks_warn, self.ks_alert)
            for sev, metric, value in (
                (psi_sev, "psi", psi_value),
                (ks_sev, "ks", ks_value),
            ):
                detection = Detection.now(
                    feature=feature,
                    metric=metric,
                    value=value,
                    severity=sev,
                    detail=(
                        f"{metric} thresholds: warn > {self.psi_stable if metric == 'psi' else self.ks_warn}, "
                        f"alert > {self.psi_warn if metric == 'psi' else self.ks_alert}"
                    ),
                )
                self._detections.append(asdict(detection))
                if sev != "ok":
                    self.alerts.raise_event(detection)

            # Remember the *worst* severity per feature (dashboard/report view).
            worst = max(psi_sev, ks_sev, key=lambda s: ("ok", "warn", "alert").index(s))
            self._feature_state[feature] = {
                "psi": psi_value,
                "ks": ks_value,
                "severity": worst,
                "last_checked_day": batch.day,
            }

        row["psi_mean"] = float(np.mean(list(row["psi"].values())))
        self._daily.append(row)

    def _evaluate_matured_labels(self, today: int, phase: str) -> None:
        """Ground truth for day ``t`` shows up once ``t + delay <= today``."""
        for pending in self._pending:
            if not pending.evaluated and pending.day + self.label_delay <= today:
                self._evaluate(pending)

    def _evaluate(self, pending: _PendingLabel) -> None:
        metrics = binary_metrics(pending.actuals, pending.predictions)
        self._trend[pending.day] = {
            "accuracy": metrics["accuracy"],
            "f1": metrics["f1"],
            "phase": pending.phase,
        }
        pending.evaluated = True
        self._flag_concept_drift(pending.day)

    def _flag_concept_drift(self, evaluated_day: int) -> None:
        """Slope-alert on the trailing window of accuracy/F1.

        Both slopes are computed; the *worst* severity becomes the day's single
        ``performance_trend`` detection (one page per day per level, not two).
        """
        acc_series = {d: v["accuracy"] for d, v in sorted(self._trend.items())}
        f1_series = {d: v["f1"] for d, v in sorted(self._trend.items())}

        acc_sev, acc_slope, n_used = trend_severity(
            acc_series, window=self.trend_window,
            slope_warn=self.slope_warn, slope_alert=self.slope_alert,
        )
        f1_sev, f1_slope, _ = trend_severity(
            f1_series, window=self.trend_window,
            slope_warn=self.slope_warn, slope_alert=self.slope_alert,
        )

        worst = max(acc_sev, f1_sev, key=lambda s: ("ok", "warn", "alert").index(s))
        if worst == "ok":
            self._concept_streak = ("ok", 0)
            return
        prev_sev, streak = self._concept_streak
        streak = streak + 1 if worst == prev_sev else 1
        self._concept_streak = (worst, streak)
        if streak < self.confirm_evals:
            # One noisy window is not a page; wait for the confirmation streak.
            return
        slope = min(acc_slope, f1_slope)
        metric = "accuracy_slope" if acc_slope <= f1_slope else "f1_slope"
        detection = Detection.now(
            feature="model_performance",
            metric=metric,
            value=slope,
            severity=worst,
            detail=(
                f"trailing {n_used}-day window: accuracy slope {acc_slope:.4f}, "
                f"f1 slope {f1_slope:.4f} (warn <= {self.slope_warn}, alert <= {self.slope_alert})"
            ),
        )
        self._detections.append(asdict(detection))
        self.alerts.raise_event(detection)

    # -- summary + persistence -------------------------------------------------

    def summary(self) -> dict[str, Any]:
        if self._last_day is None:
            return {"days": 0, "daily": [], "trend_points": [], "features": {},
                    "performance": {}, "detections": [], "alerts": [], "alert_summary": {}}
        all_actuals = np.concatenate([p.actuals for p in self._pending])
        all_preds = np.concatenate([p.predictions for p in self._pending])
        live_all = binary_metrics(all_actuals, all_preds)

        # "Live" performance is the trailing window, not the full-run average —
        # a 60-day mean hides what happened last week. The dashboard/report both
        # show this plus the full-run aggregate for context.
        trend_ordered = sorted(self._trend.items())
        recent = trend_ordered[-self.trend_window :] or trend_ordered
        if recent:
            recent_actuals = np.concatenate(
                [p.actuals for p in self._pending if p.day in {d for d, _ in recent}]
            )
            recent_preds = np.concatenate(
                [p.predictions for p in self._pending if p.day in {d for d, _ in recent}]
            )
            live_recent = binary_metrics(recent_actuals, recent_preds)
        else:
            live_recent = {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}

        phase_ranges: dict[str, list[int]] = {}
        for row in self._daily:
            phase = row["phase"]
            if phase not in phase_ranges:
                phase_ranges[phase] = [row["day"], row["day"]]
            phase_ranges[phase][1] = row["day"]

        trend_points = [{"day": d, **v} for d, v in sorted(self._trend.items())]
        daily_out = []
        for d in self._daily:
            evaluation = self._trend.get(d["day"])
            daily_out.append(
                {
                    "day": d["day"],
                    "phase": d["phase"],
                    "psi_mean": round(d["psi_mean"], 6),
                    "psi": {k: round(v, 6) for k, v in d["psi"].items()},
                    "ks": {k: round(v, 6) for k, v in d["ks"].items()},
                    "accuracy": round(evaluation["accuracy"], 6) if evaluation else None,
                    "f1": round(evaluation["f1"], 6) if evaluation else None,
                    "evaluated": evaluation is not None,
                }
            )

        return {
            "days": self._last_day,
            "label_delay": self.label_delay,
            "trend_window": self.trend_window,
            "phases": phase_ranges,
            "features": {
                name: {"psi": round(state["psi"], 6), "ks": round(state["ks"], 6), "severity": state["severity"]}
                for name, state in self._feature_state.items()
            },
            "daily": daily_out,
            "trend_points": trend_points,
            "performance": {k: round(v, 6) for k, v in live_all.items()},
            "performance_trailing": {k: round(v, 6) for k, v in live_recent.items()},
            "detections": self._detections,
            "alerts": [r.__dict__ for r in self.alerts.records()],
            "alert_summary": self.alerts.summary(),
        }

    def save(self, out_dir: str | Path) -> Path:
        """Write monitor.json + current features; alerts were already persisted."""
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        summary = self.summary()
        with (out / "monitor.json").open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2, default=str)
            handle.write("\n")
        if self._current_features is not None:
            self._current_features.to_csv(out / "current_features.csv", index=False)
        return out

    @property
    def evaluation_series(self) -> dict[int, dict[str, float]]:
        return dict(self._trend)


def run_monitoring(
    *,
    model: Any,
    manifest: dict[str, Any],
    reference: pd.DataFrame,
    days: int = 60,
    batch_size: int = 200,
    seed: int = 7,
    label_delay_days: int = 2,
    trend_window: int = 14,
    out_dir: str | Path = "runs/latest",
    max_shift: float = 0.6,
) -> dict[str, Any]:
    """Run the full monitoring loop and persist artifacts under ``out_dir``.

    Returns the summary dict (also saved as ``out_dir/monitor.json``).
    """
    out = Path(out_dir)
    # Alerts deduplicate on *simulated* time (one 24h window per production
    # day), so the clock advances as the stream advances.
    monitor_time = {"day": 1}

    def clock() -> datetime:
        return datetime.fromisoformat(_stamp_for_day(monitor_time["day"]))

    alerts = AlertManager(
        log_path=out / "alerts.log",
        json_path=out / "alerts.json",
        window_hours=24.0,
        clock=clock,
    )

    monitor = Monitor(
        model,
        reference,
        label_delay_days=label_delay_days,
        trend_window=trend_window,
        confirm_evals=2,
        alerts=alerts,
    )
    stream = StreamSimulator(days=days, batch_size=batch_size, seed=seed, max_shift=max_shift)

    logger.info("monitoring %s days of production traffic (batch=%s, seed=%s)", days, batch_size, seed)
    for batch in stream:
        monitor_time["day"] = batch.day
        monitor.observe(batch)

    monitor.save(out)
    summary = monitor.finish()

    # Re-frame model correctness: the manifest records the offline test metrics.
    summary["model"] = {
        "version": manifest.get("version"),
        "algorithm": manifest.get("algorithm"),
        "hyperparams": manifest.get("hyperparams"),
        "test_metrics": manifest.get("metrics"),
        "created_at": manifest.get("created_at"),
    }
    summary["stream"] = {
        "seed": seed,
        "batch_size": batch_size,
        "label_delay_days": label_delay_days,
        "covariate_start": stream.covariate_start,
        "concept_start": stream.concept_start,
        "max_shift": max_shift,
    }
    summary["reference"] = {
        "dataset_seed": manifest.get("dataset_seed"),
        "n_rows": manifest.get("n_rows"),
    }
    summary["alerts"] = [r.__dict__ for r in alerts.records()]
    summary["alert_summary"] = alerts.summary()
    with (out / "monitor.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, default=str)
        handle.write("\n")
    return summary


def render_report(summary: dict[str, Any]) -> str:
    """Human-readable monitoring summary for the ``report`` command."""
    lines: list[str] = []
    add = lines.append

    add("=" * 68)
    add("MODEL WATCH — monitoring report")
    add("=" * 68)

    model = summary.get("model") or {}
    add(f"\nModel v{model.get('version', '?')}  {model.get('algorithm', '?')}  "
        f"(registered {model.get('created_at', '?')[:10]})")
    test_m = model.get("test_metrics") or {}
    if test_m:
        add(f"Test set  acc={test_m.get('accuracy', float('nan')):.3f}  "
            f"f1={test_m.get('f1', float('nan')):.3f}  "
            f"auc={test_m.get('roc_auc', float('nan')):.3f}")

    phases = summary.get("phases") or {}
    if phases:
        add("\nPhases observed:")
        for name, (start, end) in phases.items():
            add(f"  {name:<16} days {start:>2}–{end:<2}")

    add("\nFeature drift (latest day):")
    add(f"  {'feature':<18}{'PSI':>8} {'':<3}{'KS':>8}  severity")
    add("  " + "-" * 46)
    for name, state in (summary.get("features") or {}).items():
        add(f"  {name:<18}{state['psi']:>8.3f} {state['ks']:>8.3f}  {state['severity']:>5}")

    performance = summary.get("performance") or {}
    if performance:
        add(f"\nLive performance over {summary.get('days', '?')} simulated days "
            f"(labels arrive +{summary.get('label_delay', 2)} days late):")
        add(f"  accuracy={performance.get('accuracy', 0):.3f}  "
            f"precision={performance.get('precision', 0):.3f}  "
            f"recall={performance.get('recall', 0):.3f}  "
            f"f1={performance.get('f1', 0):.3f}")

    trends = summary.get("trend_points") or []
    if trends:
        window = summary.get("trend_window", 14)
        tail = trends[-window:]
        if len(tail) >= 2:
            first, last = tail[0], tail[-1]
            head = f"Concept-drift window (last {len(tail)} labeled days): "
            add(f"\n{head}accuracy {first['accuracy']:.3f} → {last['accuracy']:.3f}, "
                f"f1 {first['f1']:.3f} → {last['f1']:.3f}")

    alerts_summary = summary.get("alert_summary") or {}
    add("\nAlerts:")
    add(f"  alert={alerts_summary.get('alert', 0)}  warn={alerts_summary.get('warn', 0)}")
    for record in (summary.get("alerts") or [])[:12]:
        add(f"  [{record['severity'].upper():>5}] {record['feature']:<18} "
            f"{record['metric']}={record['value']:.4f}  "
            f"x{record['count']} since {record['last_seen'][:10]}")

    add("\n" + "=" * 68)
    add("Files: runs/latest/monitor.json, alerts.json, alerts.log, current_features.csv")
    add("Dashboard: python -m model_watch dashboard  →  http://127.0.0.1:5104")
    return "\n".join(lines)
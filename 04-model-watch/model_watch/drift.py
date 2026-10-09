"""Drift detection: PSI, two-sample KS, and concept-drift trend monitoring.

Two questions a deployed model must keep answering:

1. **Are the inputs still what I trained on?** — covariate drift. Answered per
   feature with PSI (binned population shift) and the two-sample KS statistic
   (distribution shape).
2. **Is the label still what I learned?** — concept drift. Answered with a
   sliding-window trend of live accuracy/F1: when the regression slope of the
   window turns strongly negative, the label*relationship* has moved.

Everything here is computed from first principles — no scipy — so the exact
formulas are visible, documented, and unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Sequence

import numpy as np

Severity = Literal["ok", "warn", "alert"]

PSI_STABLE = 0.10
PSI_WARN = 0.25
KS_WARN = 0.20
KS_ALERT = 0.35

#: Concept-drift slope thresholds on daily accuracy/F1 (per day). A 14-day
#: window whose fit line drops faster than ``alert`` points-per-day means the
#: model is actively degrading.
SLOPE_WARN = -0.0025
SLOPE_ALERT = -0.0050


def classify(value: float, warn_at: float, alert_at: float) -> Severity:
    """Map a metric value onto ok/warn/alert using configurable thresholds."""
    if value > alert_at:
        return "alert"
    if value > warn_at:
        return "warn"
    return "ok"


@dataclass(frozen=True)
class Detection:
    """One measurement of one metric on one entity, with a severity label."""

    feature: str
    metric: str
    value: float
    severity: Severity
    timestamp: str
    detail: str = ""

    @classmethod
    def now(cls, feature: str, metric: str, value: float, severity: Severity, detail: str = "") -> "Detection":
        return cls(
            feature=feature,
            metric=metric,
            value=float(value),
            severity=severity,
            timestamp=datetime.now(timezone.utc).isoformat(),
            detail=detail,
        )


# --------------------------------------------------------------------------
# PSI — population stability index
# --------------------------------------------------------------------------

def psi(
    expected: Sequence[float],
    actual: Sequence[float],
    *,
    bins: int = 10,
    epsilon: float = 1e-8,
) -> float:
    """Population stability index between two 1-D distributions.

    The expected distribution's quantile boundaries are used as bins (so both
    sides are compared on the same scale), each bin's share is computed, and::

        PSI = Σ (actual_i - expected_i) · ln(actual_i / expected_i)

    Convention (documented in the README):
      PSI < 0.10  → stable
      0.10 ≤ PSI < 0.25 → warn (distribution is moving)
      0.25 ≤ PSI → alert (distribution has shifted)

    Identical distributions give exactly ``0.0``. ``epsilon`` guards the log of
    zero-share bins; applying it to *both* sides keeps an empty-over-empty bin
    at exactly 0.0.
    """
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)

    # Quantile edges of the reference distribution. np.unique collapses ties so
    # a constant feature degrades to a handful of edges instead of NaNs.
    if expected.size < 2 or actual.size < 2:
        raise ValueError("psi needs at least 2 samples per distribution")
    edges = np.unique(np.quantile(expected, np.linspace(0.0, 1.0, bins + 1)))
    if edges.size < 2:
        # Degenerate feature (single value): no drift is measurable in either
        # direction — both distributions are one constant bin.
        return 0.0 if float(expected[0]) == float(actual[0]) else float("inf")

    def shares(values: np.ndarray) -> np.ndarray:
        clipped = np.clip(values, edges[0], edges[-1])
        counts, _ = np.histogram(clipped, bins=edges)
        total = counts.sum()
        scaled = counts.astype(float) / total if total else counts.astype(float)
        return np.maximum(scaled, epsilon)

    expected_share = shares(expected)
    actual_share = shares(actual)
    if expected_share.shape != actual_share.shape:
        raise AssertionError("bin count mismatch between expected and actual")
    index = np.log(actual_share / expected_share)
    return float(np.sum((actual_share - expected_share) * index))


# --------------------------------------------------------------------------
# Two-sample Kolmogorov–Smirnov statistic — by hand
# --------------------------------------------------------------------------

def ks_statistic(x: Sequence[float], y: Sequence[float]) -> float:
    """Two-sample KS statistic: the largest gap between the empirical CDFs.

    ``D = sup_t |F_x(t) - F_y(t)|``. Both ECDFs are step functions, and the
    supremum over all ``t`` is attained at one of the pooled sample values, so
    evaluating both ECDFs at every pooled value and taking the max is exact.
    """
    xs = np.sort(np.asarray(x, dtype=float))
    ys = np.sort(np.asarray(y, dtype=float))
    if xs.size == 0 or ys.size == 0:
        return 1.0 if xs.size != ys.size else 0.0
    pooled = np.concatenate([xs, ys])
    cdf_x = np.searchsorted(xs, pooled, side="right") / xs.size
    cdf_y = np.searchsorted(ys, pooled, side="right") / ys.size
    return float(np.max(np.abs(cdf_x - cdf_y)))


# --------------------------------------------------------------------------
# Concept drift — sliding-window performance trend
# --------------------------------------------------------------------------

def regression_slope(values: Sequence[float]) -> float:
    """Least-squares slope of ``values`` against their 0-based index."""
    y = np.asarray(values, dtype=float)
    n = y.size
    if n < 2:
        return 0.0
    x = np.arange(n, dtype=float)
    x_mean, y_mean = x.mean(), y.mean()
    denominator = float(((x - x_mean) ** 2).sum())
    if denominator == 0.0:
        return 0.0
    return float(((x - x_mean) * (y - y_mean)).sum() / denominator)


def trend_severity(
    series: dict[int, float],
    *,
    window: int = 14,
    slope_warn: float = SLOPE_WARN,
    slope_alert: float = SLOPE_ALERT,
) -> tuple[Severity, float, int]:
    """Classify a per-day metric series by the slope of its trailing window.

    Args:
        series: day -> metric value (days must be increasing ints).
        window: how many trailing points fit the regression line.

    Returns:
        ``(severity, slope, n_used)``. With fewer than 2 points the slope is
        reported as ``ok``.
    """
    days = sorted(series)
    points = [series[d] for d in days[-window:]]
    slope = regression_slope(points)
    if len(points) < 2:
        return "ok", slope, len(points)
    if slope <= slope_alert:
        return "alert", slope, len(points)
    if slope <= slope_warn:
        return "warn", slope, len(points)
    return "ok", slope, len(points)
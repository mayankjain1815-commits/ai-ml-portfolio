"""Synthetic customer-churn data: feature sampling, labeling, and covariate shift.

The whole project is offline and deterministic, so instead of downloading a
churn dataset we generate one whose statistical properties we control exactly.
That control is what makes the drift simulation honest: we *know* the true
generating rule, so we can deliberately break it later (concept drift) or bend
the input distribution (covariate drift) and check that the monitor notices.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

#: Column order used everywhere (training, PSI reference, dashboard).
FEATURES: list[str] = [
    "tenure_months",
    "monthly_charges",
    "total_charges",
    "support_tickets",
    "contract_monthly",
    "contract_annual",
    "avg_latency_ms",
    "usage_ratio",
    "payment_failures",
]

TARGET = "churn"

#: Parametrized covariate drift applied by :func:`shift`.
#: Each entry is ``feature -> (mean_shift, std_shift)`` where the mean shift is
#: expressed in units of the feature's *reference* standard deviation and the
#: std shift is a multiplicative change. ``magnitude`` in :func:`shift` scales
#: both toward the target, so 0.0 = no drift and 1.0 = full drift.
SHIFT_SPEC: dict[str, tuple[float, float]] = {
    "tenure_months": (-0.75, 0.15),        # newer customers dominate
    "monthly_charges": (0.65, 0.20),       # price tier creeps up
    "total_charges": (-0.55, 0.25),
    "support_tickets": (0.60, 0.35),       # support load gets worse
    "contract_monthly": (0.35, 0.00),      # mix tilts to month-to-month
    "contract_annual": (-0.20, 0.00),
    "avg_latency_ms": (0.90, 0.30),        # service slows down
    "usage_ratio": (-0.60, 0.20),          # customers engage less
    "payment_failures": (0.45, 0.40),
}


@dataclass(frozen=True)
class Dataset:
    """A labeled dataset plus the parameters it was generated with."""

    frame: pd.DataFrame
    seed: int

    @property
    def x(self) -> pd.DataFrame:
        return self.frame[FEATURES]

    @property
    def y(self) -> pd.Series:
        return self.frame[TARGET]


def sample_features(n: int, rng: np.random.Generator) -> pd.DataFrame:
    """Draw ``n`` rows of realistic, mildly correlated churn features."""
    tenure = np.clip(rng.uniform(1, 72, n), 1, 72)
    monthly = np.clip(rng.normal(70.0, 25.0, n), 15.0, 160.0)

    # contract_type: month-to-month / one-year / two-year.
    contract = rng.choice(3, size=n, p=[0.55, 0.20, 0.25])
    contract_monthly = (contract == 0).astype(float)
    contract_annual = (contract == 1).astype(float)

    # Total charges track tenure x price, with billing noise (discounts, credits).
    noise = np.clip(rng.normal(1.0, 0.08, n), 0.7, 1.3)
    total = np.clip(tenure * monthly * noise, 0.0, None)

    frame = pd.DataFrame(
        {
            "tenure_months": tenure,
            "monthly_charges": monthly,
            "total_charges": total,
            "support_tickets": rng.poisson(1.2, n).astype(float),
            "contract_monthly": contract_monthly,
            "contract_annual": contract_annual,
            "avg_latency_ms": np.clip(rng.lognormal(np.log(120.0), 0.45, n), 30.0, 600.0),
            "usage_ratio": np.clip(rng.beta(2.2, 2.0, n), 0.0, 1.0),
            "payment_failures": rng.poisson(0.30, n).astype(float),
        }
    )
    return frame[FEATURES]


def churn_probability(frame: pd.DataFrame, *, concept: str = "v1", rng: np.random.Generator | None = None) -> pd.Series:
    """P(churn) under the *true* rule — this is P(y|x), the thing we later break.

    ``concept="v1"`` is the rule the model learns in training (test AUC ~0.81).
    ``concept="v2"`` is the post-drift world: long-tenure customers start leaving
    (competition poaches them), heavy users leave (usage-based pricing hurts),
    and month-to-month stops being the red flag it once was. The features look
    similar but the *relationship* between features and churn has moved — the
    definition of concept drift. The centered delta keeps the churn rate roughly
    stable so the damage comes from the rotated boundary, not a prior shift.
    """
    logit = (
        -2.80
        - 0.065 * frame["tenure_months"]
        + 0.020 * frame["monthly_charges"]
        + 0.0005 * frame["total_charges"]
        + 0.60 * frame["support_tickets"]
        + 1.25 * frame["contract_monthly"]
        - 0.65 * frame["contract_annual"]
        + 0.005 * frame["avg_latency_ms"]
        - 1.80 * frame["usage_ratio"]
        + 0.90 * frame["payment_failures"]
    )
    if concept == "v2":
        logit = logit + (
            0.050 * (frame["tenure_months"] - 36.5)
            - 0.018 * (frame["monthly_charges"] - 70.0)
            + 1.60 * (frame["usage_ratio"] - 0.52)
            - 1.00 * (frame["contract_monthly"] - 0.55)
        )
    elif concept != "v1":
        raise ValueError(f"unknown concept {concept!r} (expected 'v1' or 'v2')")

    if rng is not None:
        logit = logit + rng.normal(0.0, 0.55, len(frame))
    return pd.Series(1.0 / (1.0 + np.exp(-logit)), index=frame.index, name=TARGET)


def label(frame: pd.DataFrame, *, concept: str = "v1", rng: np.random.Generator | None = None) -> pd.Series:
    """Bernoulli-draw the churn label from :func:`churn_probability`."""
    proba = churn_probability(frame, concept=concept, rng=rng)
    draws = np.random.default_rng(0).random(len(proba)) if rng is None else rng.random(len(proba))
    return pd.Series((draws < proba.to_numpy()).astype(int), index=frame.index, name=TARGET)


def generate(n_rows: int = 12_000, *, seed: int = 42, concept: str = "v1") -> Dataset:
    """Generate the full labeled churn dataset (seeded, deterministic)."""
    rng = np.random.default_rng(seed)
    frame = sample_features(n_rows, rng)
    frame[TARGET] = label(frame, concept=concept, rng=rng)
    return Dataset(frame=frame, seed=seed)


def shift(
    frame: pd.DataFrame,
    magnitude: float,
    *,
    spec: dict[str, tuple[float, float]] | None = None,
    stats: dict[str, tuple[float, float]] | None = None,
) -> pd.DataFrame:
    """Apply parametrized covariate drift to ``frame``.

    ``magnitude`` in [0, 1] scales every entry of ``spec``: at 0 the frame is
    unchanged, at 1 each feature reaches ``mean + magnitude * mean_shift * std``
    with its standard deviation multiplied by ``1 + magnitude * std_shift``.
    The transform is deterministic (a location/scale map of the observed
    values), so the same input and magnitude always produce the same output.

    Args:
        frame: Features to bend. Only columns present in the spec are touched.
        magnitude: Drift intensity, clamped to [0, 1].
        spec: Override the default :data:`SHIFT_SPEC`.
        stats: Reference ``(mean, std)`` per column; computed from ``frame``
            when omitted. The monitor passes *training* statistics here so the
            shift is defined against the distribution the model learned.
    """
    if not 0.0 <= magnitude <= 1.0:
        raise ValueError(f"magnitude must be in [0, 1], got {magnitude}")
    spec = SHIFT_SPEC if spec is None else spec
    out = frame.copy()
    if magnitude == 0.0:
        return out

    for column, (mean_shift, std_shift) in spec.items():
        if column not in out.columns:
            continue
        values = out[column].to_numpy(dtype=float)
        if stats is not None and column in stats:
            ref_mean, ref_std = stats[column]
        else:
            ref_mean, ref_std = float(values.mean()), float(values.std())
        if ref_std == 0.0:
            ref_std = 1.0
        if set(values.tolist()) <= {0.0, 1.0}:
            # Binary/one-hot columns: drift changes *prevalence*, so deterministically
            # flip rows (the rows are i.i.d., so flipping by position == flipping
            # at random) instead of rescaling 0/1 into invalid fractions.
            prevalence = float(values.mean())
            delta = magnitude * mean_shift * 0.5
            target = float(np.clip(prevalence + delta, 0.02, 0.98))
            flips = int(round((target - prevalence) * len(values)))
            if flips > 0:
                zeros = np.flatnonzero(values < 0.5)[:flips]
                values[zeros] = 1.0
            elif flips < 0:
                ones = np.flatnonzero(values > 0.5)[:-flips]
                values[ones] = 0.0
            out[column] = values
        else:
            new_mean = ref_mean + magnitude * mean_shift * ref_std
            new_std = ref_std * (1.0 + magnitude * std_shift)
            out[column] = new_mean + (values - ref_mean) * (new_std / ref_std)
    return out[FEATURES] if set(FEATURES) <= set(out.columns) else out


def reference_stats(frame: pd.DataFrame) -> dict[str, tuple[float, float]]:
    """Per-column ``(mean, std)`` of the reference (training) frame."""
    return {
        column: (float(frame[column].mean()), float(frame[column].std()))
        for column in frame.columns
        if column != TARGET
    }

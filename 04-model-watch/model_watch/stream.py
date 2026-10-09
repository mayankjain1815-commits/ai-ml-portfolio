"""A 60-day simulated production stream of churn-scoring traffic.

Each "day" is a batch of ~200 customer records, generated deterministically
(seed + day → RNG) so every run of the demo replays identically. The story the
stream tells:

* **days 1–19** — normal production: same distribution the model trained on.
* **days 20–44** — gradual *covariate* drift: :func:`model_watch.data_gen.shift`
  bends the input distribution with an intensity that ramps from 0 to full.
  P(churn|x) is untouched, so the model's decision rule is still *correct* —
  the inputs just move away from training.
* **days 45–60** — *concept* drift: the churn rule itself changes (v2). Features
  keep their drifted shape but the relationship between features and churn now
  opposes what the model learned, so accuracy degrades.

Ground truth is attached to every batch but the monitor obeys a label delay and
only *consumes* a batch's labels a couple of days after it was scored — the way
churn actually becomes known in production.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import numpy as np
import pandas as pd

from model_watch.data_gen import (
    TARGET,
    churn_probability,
    reference_stats,
    sample_features,
    shift,
)


@dataclass(frozen=True)
class Batch:
    """One simulated day of production traffic."""

    day: int
    features: pd.DataFrame
    target: pd.Series
    phase: str


class StreamSimulator:
    """Yields one :class:`Batch` per simulated day, always in the same order."""

    def __init__(
        self,
        *,
        days: int = 60,
        batch_size: int = 200,
        seed: int = 7,
        covariate_start: int | None = None,
        concept_start: int | None = None,
        max_shift: float = 0.6,
    ) -> None:
        if days < 3:
            raise ValueError("stream needs at least 3 days to show the phases")
        self.days = days
        self.batch_size = batch_size
        self.seed = seed
        # Phase boundaries scale with the run length so `--days 30` still shows
        # the full arc; the defaults reproduce day 20 / day 45 at 60 days.
        self.covariate_start = covariate_start or max(1, days * 20 // 60)
        self.concept_start = concept_start or max(self.covariate_start + 1, days * 45 // 60)
        if not self.covariate_start < self.concept_start <= days:
            raise ValueError("need covariate_start < concept_start <= days")
        self.max_shift = max_shift

    def _phase(self, day: int) -> str:
        if day < self.covariate_start:
            return "normal"
        if day < self.concept_start:
            return "covariate_drift"
        return "concept_drift"

    def _magnitude(self, day: int) -> float:
        """Ramp covariate-drift intensity 0 → max over the covariate period."""
        if day < self.covariate_start:
            return 0.0
        ramp = (day - self.covariate_start + 1) / (self.concept_start - self.covariate_start)
        return float(min(self.max_shift, self.max_shift * ramp))

    def __iter__(self) -> Iterator[Batch]:
        # Reference distribution the drift is defined against, rebuilt from the
        # same generator the training set came from.
        ref = sample_features(2_000, np.random.default_rng(3_147))
        stats = reference_stats(ref)

        for day in range(1, self.days + 1):
            rng = np.random.default_rng([self.seed, day])
            frame = sample_features(self.batch_size, rng)
            magnitude = self._magnitude(day)
            if magnitude > 0.0:
                frame = shift(frame, magnitude, stats=stats)

            concept = "v2" if day >= self.concept_start else "v1"
            label_rng = np.random.default_rng([self.seed, day, 2])
            proba = churn_probability(frame, concept=concept, rng=label_rng)
            target = pd.Series(
                (label_rng.random(self.batch_size) < proba.to_numpy()).astype(int),
                index=frame.index,
                name=TARGET,
            )
            yield Batch(day=day, features=frame, target=target, phase=self._phase(day))
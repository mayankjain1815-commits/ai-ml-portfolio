"""Train, evaluate, and select the churn model.

Two candidate algorithms race on the same held-out test split; the winner
(ROC-AUC, ties broken by F1) is what gets registered and monitored. The point
of this module is not the model — it is producing a *frozen, versioned artifact*
plus honest metrics that the monitor can later compare against live behavior.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

from model_watch.data_gen import FEATURES, TARGET, generate
from model_watch.metrics import accuracy as hand_accuracy
from model_watch.metrics import f1 as hand_f1

TEST_SIZE = 0.2


@dataclass
class TrainResult:
    """Everything the registry needs to freeze a version."""

    model: Pipeline | RandomForestClassifier
    algorithm: str
    hyperparams: dict[str, Any]
    metrics: dict[str, float]
    candidate_metrics: dict[str, dict[str, float]]
    feature_names: list[str]
    dataset_hash: str
    dataset_seed: int
    n_rows: int
    hand_check: dict[str, float] = field(default_factory=dict)

    @property
    def auc(self) -> float:
        return self.metrics["roc_auc"]


def dataset_hash(frame: pd.DataFrame) -> str:
    """Stable SHA-256 over the CSV rendering of the dataset (order-sensitive)."""
    payload = frame.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _score(model: Any, x: pd.DataFrame, y: pd.Series) -> dict[str, float]:
    """Standard five-metric view of a fitted binary classifier."""
    proba = model.predict_proba(x)[:, 1]
    pred = (proba >= 0.5).astype(int)
    return {
        "accuracy": float(accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, proba)),
    }


def train(seed: int = 42, n_rows: int = 12_000) -> TrainResult:
    """Generate data, race two models, return the winner with full evidence.

    The hand-computed accuracy/F1 of the winning model are kept alongside the
    sklearn numbers (``hand_check``); they must match, which is exactly what
    the metric tests assert on toy inputs too.
    """
    dataset = generate(n_rows, seed=seed)
    x, y = dataset.x, dataset.y
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=TEST_SIZE, random_state=seed, stratify=y
    )

    candidates: dict[str, Any] = {
        "logistic_regression": make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1_000, random_state=seed),
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200, random_state=seed, n_jobs=-1
        ),
    }

    candidate_metrics: dict[str, dict[str, float]] = {}
    for name, model in candidates.items():
        model.fit(x_train, y_train)
        candidate_metrics[name] = _score(model, x_test, y_test)

    # Winner: ROC-AUC first (threshold-free), F1 as the tie-break.
    winner_name = max(
        candidate_metrics,
        key=lambda n: (candidate_metrics[n]["roc_auc"], candidate_metrics[n]["f1"]),
    )
    model = candidates[winner_name]
    metrics = candidate_metrics[winner_name]

    proba = model.predict_proba(x_test)[:, 1]
    pred = (proba >= 0.5).astype(int)
    hand_check = {
        "accuracy": hand_accuracy(y_test, pred),
        "f1": hand_f1(y_test, pred),
    }
    if not np.isclose(hand_check["accuracy"], metrics["accuracy"], atol=1e-12):
        raise AssertionError("hand accuracy disagrees with sklearn")
    if not np.isclose(hand_check["f1"], metrics["f1"], atol=1e-9):
        raise AssertionError("hand F1 disagrees with sklearn")

    hyperparams = {
        "logistic_regression": {"max_iter": 1_000, "scaled": True},
        "random_forest": {"n_estimators": 200},
    }[winner_name]

    return TrainResult(
        model=model,
        algorithm=winner_name,
        hyperparams=hyperparams,
        metrics=metrics,
        candidate_metrics=candidate_metrics,
        feature_names=list(FEATURES),
        dataset_hash=dataset_hash(dataset.frame),
        dataset_seed=seed,
        n_rows=n_rows,
        hand_check=hand_check,
    )


def reference_frame(seed: int = 42, n_rows: int = 12_000) -> pd.DataFrame:
    """Regenerate the exact training frame the model was fitted on.

    Deterministic generation plus the stored seed means the monitor rebuilds the
    PSI reference distribution without shipping a 12k-row CSV — and the hash in
    the manifest proves it is the same data the model saw.
    """
    return generate(n_rows, seed=seed).frame

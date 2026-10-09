"""Binary-classification metrics computed from first principles.

The monitor computes *live* accuracy/F1 from late-arriving labels with these
functions (scikit-learn is a training-time dependency, not a runtime one), and
the test suite verifies every function here against scikit-learn's version on
identical inputs. If the hand math and sklearn ever disagree, the tests fail.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

LabelLike = Sequence[int] | np.ndarray


def confusion_counts(y_true: LabelLike, y_pred: LabelLike) -> tuple[int, int, int, int]:
    """Return ``(tp, fp, tn, fn)`` for binary 0/1 labels."""
    true = np.asarray(y_true, dtype=int)
    pred = np.asarray(y_pred, dtype=int)
    if true.shape != pred.shape:
        raise ValueError(f"shape mismatch: y_true {true.shape} vs y_pred {pred.shape}")
    if true.size == 0:
        raise ValueError("cannot compute metrics on empty inputs")
    tp = int(np.sum((true == 1) & (pred == 1)))
    fp = int(np.sum((true == 0) & (pred == 1)))
    tn = int(np.sum((true == 0) & (pred == 0)))
    fn = int(np.sum((true == 1) & (pred == 0)))
    return tp, fp, tn, fn


def accuracy(y_true: LabelLike, y_pred: LabelLike) -> float:
    """(TP + TN) / total."""
    tp, fp, tn, fn = confusion_counts(y_true, y_pred)
    return (tp + tn) / (tp + fp + tn + fn)


def precision(y_true: LabelLike, y_pred: LabelLike) -> float:
    """TP / (TP + FP); 0.0 when the model never predicts the positive class."""
    tp, fp, _, _ = confusion_counts(y_true, y_pred)
    return tp / (tp + fp) if (tp + fp) else 0.0


def recall(y_true: LabelLike, y_pred: LabelLike) -> float:
    """TP / (TP + FN); 0.0 when there are no positive examples."""
    tp, _, _, fn = confusion_counts(y_true, y_pred)
    return tp / (tp + fn) if (tp + fn) else 0.0


def f1(y_true: LabelLike, y_pred: LabelLike) -> float:
    """Harmonic mean of precision and recall; 0.0 when both are 0."""
    p, r = precision(y_true, y_pred), recall(y_true, y_pred)
    return 2 * p * r / (p + r) if (p + r) else 0.0


def roc_auc(y_true: LabelLike, y_score: LabelLike) -> float:
    """AUC via the Mann-Whitney U statistic: the probability that a random
    positive example scores higher than a random negative one, with ties
    counted as half — computed with average ranks so tie handling matches
    sklearn's ``roc_auc_score`` exactly.
    """
    true = np.asarray(y_true, dtype=int)
    score = np.asarray(y_score, dtype=float)
    n_pos = int(np.sum(true == 1))
    n_neg = int(np.sum(true == 0))
    if n_pos == 0 or n_neg == 0:
        raise ValueError("roc_auc requires both classes present")

    order = np.argsort(score, kind="mergesort")
    ranks = np.empty(len(score), dtype=float)
    sorted_scores = score[order]
    i = 0
    while i < len(score):
        j = i
        while j + 1 < len(score) and sorted_scores[j + 1] == sorted_scores[i]:
            j += 1
        ranks[order[i : j + 1]] = (i + j) / 2.0 + 1.0  # average rank, 1-based
        i = j + 1

    rank_sum_pos = float(ranks[true == 1].sum())
    u = rank_sum_pos - n_pos * (n_pos + 1) / 2.0
    return u / (n_pos * n_neg)


def binary_metrics(y_true: LabelLike, y_pred: LabelLike) -> dict[str, float]:
    """Accuracy/precision/recall/F1 in one dict (the monitor's late-label view)."""
    return {
        "accuracy": accuracy(y_true, y_pred),
        "precision": precision(y_true, y_pred),
        "recall": recall(y_true, y_pred),
        "f1": f1(y_true, y_pred),
    }

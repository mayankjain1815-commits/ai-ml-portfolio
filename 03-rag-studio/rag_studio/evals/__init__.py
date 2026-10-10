"""Evaluation subpackage: hand-implemented retrieval and answer metrics.

Import from here or run the harness through the CLI:

    python -m rag_studio eval
"""

from rag_studio.evals.harness import load_questions, run_evaluation
from rag_studio.evals.metrics import (
    faithfulness,
    keyword_coverage,
    mean_reciprocal_rank,
    recall_at_k,
)

__all__ = [
    "faithfulness",
    "keyword_coverage",
    "load_questions",
    "mean_reciprocal_rank",
    "recall_at_k",
    "run_evaluation",
]

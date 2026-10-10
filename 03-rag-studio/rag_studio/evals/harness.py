"""The eval harness: run a labeled question set through the live pipeline.

This is the part that turns "it seems to work" into numbers. For each question
in ``data/evals.json`` the harness retrieves the top ``max(ks)`` chunks, finds
the rank of the first chunk from the question's gold source, generates an
answer with the *same* pipeline the CLI uses, and scores it. The resulting
report separates retrieval problems (recall/MRR) from generation problems
(faithfulness/keyword coverage) and records latency.

The k-sweep is the headline: recall@1 <= recall@3 <= recall@5 shows whether the
right document is merely surfaced or actually ranked first, which is exactly the
distinction that matters when only the top few chunks reach the generator.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from rag_studio.generate import compose
from rag_studio.index import TfidfIndex
from rag_studio.retriever import retrieve
from rag_studio.evals.metrics import (
    faithfulness,
    keyword_coverage,
    mean_reciprocal_rank,
    recall_at_k,
)

DEFAULT_KS = (1, 3, 5)
DEFAULT_DATASET = Path(__file__).resolve().parents[2] / "data" / "evals.json"


@dataclass(frozen=True)
class Question:
    """One labeled eval question and the document that answers it."""

    id: str
    question: str
    source: str  # gold source file name
    keywords: tuple[str, ...]  # words a correct answer is expected to contain


def load_questions(path: str | Path | None = None) -> list[Question]:
    """Load the labeled dataset (bundled by default)."""
    dataset_path = Path(path) if path is not None else DEFAULT_DATASET
    if not dataset_path.is_file():
        raise FileNotFoundError(f"eval dataset not found: {dataset_path}")
    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    return [
        Question(
            id=entry["id"],
            question=entry["question"],
            source=entry["source"],
            keywords=tuple(entry.get("gold_keywords", [])),
        )
        for entry in raw["questions"]
    ]


def run_evaluation(
    index: TfidfIndex,
    questions: list[Question],
    *,
    ks: tuple[int, ...] = DEFAULT_KS,
    api_key: str | None = None,
    report_path: str | Path | None = None,
) -> dict:
    """Score `questions` against `index` and optionally write a JSON report."""
    if not ks or any(k < 1 for k in ks):
        raise ValueError("ks must contain positive integers")
    ks = tuple(sorted(set(ks)))
    max_k = max(ks)

    records = []
    ranks: list[int | None] = []
    for question in questions:
        started = perf_counter()
        result = retrieve(index, question.question, k=max_k, api_key=api_key)
        retrieved_at = perf_counter()
        text, mode = compose(question.question, result.hits, api_key=api_key)
        finished = perf_counter()

        gold_rank = next(
            (rank for rank, hit in enumerate(result.hits, start=1) if hit.chunk.source == question.source),
            None,
        )
        ranks.append(gold_rank)
        records.append(
            {
                "id": question.id,
                "question": question.question,
                "source": question.source,
                "gold_rank": gold_rank,
                "recall": {str(k): gold_rank is not None and gold_rank <= k for k in ks},
                "reciprocal_rank": 0.0 if gold_rank is None else 1.0 / gold_rank,
                "faithfulness": faithfulness(text, [hit.chunk.text for hit in result.hits]),
                "keyword_coverage": keyword_coverage(text, question.keywords),
                "latency_ms": (finished - started) * 1000.0,
                "retrieval_ms": (retrieved_at - started) * 1000.0,
                "mode": mode,
                "answer": text,
                "citations": [
                    {
                        "chunk_id": hit.chunk.id,
                        "source": hit.chunk.source,
                        "position": hit.chunk.position,
                        "score": round(hit.score, 6),
                    }
                    for hit in result.hits
                ],
            }
        )

    count = len(records) or 1
    overall = {
        "questions": len(records),
        "recall_at_k": {str(k): recall_at_k(ranks, k) for k in ks},
        "mrr": mean_reciprocal_rank(ranks),
        "faithfulness": sum(r["faithfulness"] for r in records) / count,
        "keyword_coverage": sum(r["keyword_coverage"] for r in records) / count,
        "latency_ms_mean": sum(r["latency_ms"] for r in records) / count,
    }
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "index": {"mode": index.mode, "chunks": len(index.chunks)},
        "ks": list(ks),
        "overall": overall,
        "questions": records,
    }
    if report_path is not None:
        path = Path(report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def format_report(report: dict) -> str:
    """Render a report as a plain-ASCII table plus a summary block."""
    ks = report["ks"]
    headers = ["id", "rank", *(f"R@{k}" for k in ks), "faith", "kw", "ms", "question"]
    rows = []
    for record in report["questions"]:
        rows.append(
            [
                record["id"],
                "-" if record["gold_rank"] is None else str(record["gold_rank"]),
                *("ok" if record["recall"][str(k)] else "--" for k in ks),
                f"{record['faithfulness']:.2f}",
                f"{record['keyword_coverage']:.2f}",
                f"{record['latency_ms']:.1f}",
                _truncate(record["question"], 52),
            ]
        )
    lines = [_ascii_table(headers, rows), ""]
    overall = report["overall"]
    recalls = "   ".join(f"recall@{k} {overall['recall_at_k'][str(k)]:.2f}" for k in ks)
    lines.append(f"  {recalls}")
    lines.append(
        f"  MRR {overall['mrr']:.2f}   faithfulness {overall['faithfulness']:.2f}   "
        f"keyword coverage {overall['keyword_coverage']:.2f}   "
        f"mean latency {overall['latency_ms_mean']:.1f} ms"
    )
    lines.append(
        f"  {overall['questions']} questions   index: {report['index']['chunks']} chunks "
        f"({report['index']['mode']})"
    )
    return "\n".join(lines)


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 3] + "..."


def _ascii_table(headers: list[str], rows: list[list[str]]) -> str:
    """Minimal ASCII table: +---+ borders, no dependencies, no colour."""
    columns = len(headers)
    widths = [len(headers[i]) for i in range(columns)]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    separator = "+" + "+".join("-" * (width + 2) for width in widths) + "+"

    def render(row: list[str]) -> str:
        cells = (cell.ljust(widths[i]) for i, cell in enumerate(row))
        return "| " + " | ".join(cells) + " |"

    lines = [separator, render(headers), separator]
    lines.extend(render(row) for row in rows)
    lines.append(separator)
    return "\n".join(lines)

"""Tests for the eval metrics and the offline harness."""

from pathlib import Path

import pytest

from rag_studio.chunker import chunk_documents
from rag_studio.evals.harness import (
    format_report,
    load_questions,
    run_evaluation,
)
from rag_studio.evals.metrics import (
    faithfulness,
    keyword_coverage,
    mean_reciprocal_rank,
    recall_at_k,
)
from rag_studio.index import build_index
from rag_studio.ingest import document_from_text, load_directory


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------


def test_recall_at_k_basic():
    # questions 1 and 3 have their gold source inside the top k, question 2 misses
    assert recall_at_k([1, None, 2], k=2) == pytest.approx(2 / 3)


def test_recall_at_k_edge_cases():
    assert recall_at_k([], k=3) == 0.0
    assert recall_at_k([1, 1, 1], k=1) == 1.0
    with pytest.raises(ValueError):
        recall_at_k([1], k=0)


def test_mean_reciprocal_rank():
    assert mean_reciprocal_rank([1, 2, None]) == pytest.approx((1.0 + 0.5) / 3)
    assert mean_reciprocal_rank([]) == 0.0


def test_faithfulness_grounding():
    assert faithfulness("packet header", ["packet header routing data"]) == 1.0
    assert faithfulness("The moon is made of green cheese.", ["packets and routers"]) == 0.0
    # empty answer is trivially grounded; empty contexts with words are not
    assert faithfulness("", ["anything"]) == 1.0
    assert faithfulness("some words", []) == 0.0


def test_keyword_coverage_needs_all_content_words():
    # a multi-word keyword hits only when every content word is present
    assert keyword_coverage("the server returned a 404", ["status code", "404"]) == 0.5
    assert keyword_coverage("a 404 means the page was not found", ["404"]) == 1.0
    assert keyword_coverage("the server returned a 404 status code", ["status code"]) == 1.0
    assert keyword_coverage("anything", []) == 1.0


# ---------------------------------------------------------------------------
# bundled dataset + harness
# ---------------------------------------------------------------------------


def test_bundled_evals_dataset_loads():
    questions = load_questions()
    assert len(questions) >= 10
    sources = {q.source for q in questions}
    assert len(sources) == 5  # one doc per bundled article
    assert all(q.question and q.source and q.keywords for q in questions)


def _bundled_index():
    docs_dir = Path(__file__).resolve().parents[1] / "data" / "docs"
    documents = load_directory(docs_dir)
    return build_index(chunk_documents(documents), mode="tfidf")


def test_run_evaluation_full_pipeline(tmp_path):
    index = _bundled_index()
    questions = load_questions()
    report = run_evaluation(index, questions, ks=(1, 3, 5), report_path=tmp_path / "r.json")

    # report structure
    assert report["index"]["chunks"] >= 5
    assert report["overall"]["questions"] == len(questions)
    # retrieval should recover the gold source for most questions
    assert report["overall"]["recall_at_k"]["5"] >= 0.5
    assert report["overall"]["mrr"] >= 0.0
    # extractive answers are verbatim, so faithfulness should be high
    assert report["overall"]["faithfulness"] >= 0.75
    # per-question records carry citations and an answer
    assert report["questions"][0]["answer"]
    assert report["questions"][0]["citations"]
    # report persisted
    assert (tmp_path / "r.json").is_file()


def test_run_evaluation_ks_sweep_is_anchored():
    index = _bundled_index()
    report = run_evaluation(index, load_questions(), ks=(1, 5))
    recall = report["overall"]["recall_at_k"]
    assert recall["1"] <= recall["5"]


def test_run_evaluation_rejects_bad_ks():
    index = _bundled_index()
    with pytest.raises(ValueError, match="positive integers"):
        run_evaluation(index, [], ks=(0,))


def test_format_report_renders_table():
    index = _bundled_index()
    report = run_evaluation(index, load_questions(), ks=(1, 3, 5))
    text = format_report(report)
    assert "+--" in text  # ASCII table borders
    assert "recall@1" in text and "MRR" in text
    assert "questions" in text
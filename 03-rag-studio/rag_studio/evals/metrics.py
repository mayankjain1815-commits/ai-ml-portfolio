"""Metrics for the RAG eval harness, all implemented by hand.

The point of these metrics is to separate the two failure modes of a RAG
system: retrieval can miss the right document, and generation can say things
the documents never said. ``recall@k`` and ``MRR`` measure the first;
``faithfulness`` is a lexical proxy for the second.

Relevance here is document-level: a retrieved chunk counts as relevant when it
comes from the question's gold source file. ``keyword_coverage`` adds a softer
answer-quality signal: how many of the gold answer keywords the answer contains.
"""

from __future__ import annotations

from collections.abc import Sequence

from rag_studio.text import content_words


def recall_at_k(ranks: Sequence[int | None], k: int) -> float:
    """Fraction of questions whose gold source appears in the top `k` hits.

    `ranks` holds the 1-based rank of the first relevant chunk per question
    (None when nothing relevant was retrieved).
    """
    if k < 1:
        raise ValueError("k must be at least 1")
    if not ranks:
        return 0.0
    hits = sum(1 for rank in ranks if rank is not None and rank <= k)
    return hits / len(ranks)


def mean_reciprocal_rank(ranks: Sequence[int | None]) -> float:
    """Mean of 1/rank of the first relevant chunk (0 for a miss)."""
    if not ranks:
        return 0.0
    total = sum(0.0 if rank is None else 1.0 / rank for rank in ranks)
    return total / len(ranks)


def faithfulness(answer: str, contexts: Sequence[str]) -> float:
    """Fraction of the answer's content words that appear in the retrieved chunks.

    This is a lexical grounding proxy, not a judgment of meaning: an answer can
    be grounded word-for-word and still be wrong. It catches the common failure
    where the generator invents entities that are in no source. An empty answer
    scores 1.0 (there is nothing ungrounded to find); an answer with words but
    no contexts scores 0.0.
    """
    answer_words = content_words(answer)
    if not answer_words:
        return 1.0
    context_words: set[str] = set()
    for context in contexts:
        context_words |= content_words(context)
    if not context_words:
        return 0.0
    return len(answer_words & context_words) / len(answer_words)


def keyword_coverage(answer: str, keywords: Sequence[str]) -> float:
    """Fraction of gold answer keywords present in the answer.

    A keyword hits when all of its content words appear in the answer, so a
    multi-word phrase like "status code" is only credited when both content
    words are present — never by one of them alone.
    """
    if not keywords:
        return 1.0
    answer_words = content_words(answer)
    hits = 0
    for keyword in keywords:
        wanted = content_words(keyword)
        if wanted and wanted <= answer_words:
            hits += 1
    return hits / len(keywords)

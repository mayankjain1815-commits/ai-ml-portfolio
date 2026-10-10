"""Turn retrieved chunks into an answer, in demo mode or with Gemini.

Demo mode is not a stub: it is a second implementation of the generation step.
It scores every sentence in the retrieved chunks by (query-term overlap) x
(chunk cosine score), stitches the best 2-4 into a readable answer, and appends
``[n]`` citations that map to the retrieval order. Because sentences are copied
verbatim, the result is grounded by construction — faithfulness is ~1.0 and the
citations are always correct.

Real mode prompts Gemini with the numbered chunks, forces the same ``[n]``
citation format, then post-verifies the output and removes any citation index
that does not exist (models sometimes hallucinate ``[7]`` for five sources).
If the model call fails, generation falls back to the extractive path rather
than erroring the user out.

Both paths return the same shape: answer text, the (chunk, score) hits used, and
the wall-clock latency of retrieve + generate.
"""

from __future__ import annotations

import logging
import re
import time
from collections import Counter
from dataclasses import dataclass

from rag_studio import llm
from rag_studio.index import TfidfIndex
from rag_studio.retriever import (
    DEFAULT_K,
    DEFAULT_MMR_LAMBDA,
    ScoredChunk,
    retrieve,
)
from rag_studio.text import split_sentences, tokenize

logger = logging.getLogger(__name__)

_MIN_SENTENCES = 2
_MAX_SENTENCES = 4
_MAX_SENTENCES_PER_CHUNK = 2
_MIN_WORDS_PER_SENTENCE = 6
_RELATIVE_SCORE_FLOOR = 0.15  # ignore sentences scoring below this share of the best

_MARKDOWN_HEADING_RE = re.compile(r"(?m)^[ \t]*#{1,6}[^\n]*\n?")

_NO_HITS_MESSAGE = (
    "I could not find any relevant passages in the index. Try adding documents "
    "to data/docs and rebuilding, or rephrase the question."
)

_ANSWER_SYSTEM = "You answer strictly from the provided sources and always cite them."
_ANSWER_PROMPT = """\
Answer the question in 2-4 sentences using ONLY the sources below.
End every sentence with a citation like [1] or [2]. If the sources do not
contain the answer, say so plainly.

Sources:
{sources}

Question: {question}

Answer:"""

_CITATION_RE = re.compile(r"\[(\d+)\]")


@dataclass
class Answer:
    """The full result of one question: text, supporting hits, and timing."""

    text: str
    hits: list[ScoredChunk]
    latency_ms: float
    mode: str  # "extractive" (demo) or "gemini" (real)
    queries: list[str]


@dataclass(frozen=True)
class _Candidate:
    """A sentence offered up as part of the extractive answer."""

    sentence: str
    score: float
    chunk_rank: int  # 0-based position in the retrieval order
    sentence_index: int  # 0-based position inside its chunk


def verify_citations(text: str, n_sources: int) -> str:
    """Drop citation markers that point at sources which don't exist.

    Returns the text with out-of-range ``[n]`` removed and the leftover
    punctuation/spacing tidied, so a hallucinated ``[9]`` never reaches a user.
    """
    def replace(match: re.Match) -> str:
        index = int(match.group(1))
        return match.group(0) if 1 <= index <= n_sources else ""

    cleaned = _CITATION_RE.sub(replace, text)
    cleaned = re.sub(r"\s+([.,!?;:])", r"\1", cleaned)
    return re.sub(r"[ \t]{2,}", " ", cleaned).strip()


def _eligible(sentence: str) -> bool:
    """A sentence is quotable if it is long enough and ends like a sentence."""
    words = sentence.split()
    return (
        len(words) >= _MIN_WORDS_PER_SENTENCE
        and sentence.rstrip().endswith((".", "?", "!"))
    )


def _extractive_answer(question: str, hits: list[ScoredChunk]) -> str:
    """Score sentences by overlap x chunk score and stitch the best few together."""
    if not hits:
        return _NO_HITS_MESSAGE

    question_terms = set(tokenize(question))
    best_by_sentence: dict[str, _Candidate] = {}
    for chunk_rank, hit in enumerate(hits):
        # Drop markdown headings: quoting "# DNS: The Internet's Address Book"
        # as a sentence makes the answer look like a fragment.
        body = _MARKDOWN_HEADING_RE.sub("", hit.chunk.text)
        for sentence_index, sentence in enumerate(split_sentences(body)):
            if not _eligible(sentence):
                continue
            terms = set(tokenize(sentence))
            overlap = (
                len(question_terms & terms) / len(question_terms) if question_terms else 0.0
            )
            candidate = _Candidate(
                sentence=sentence,
                score=overlap * hit.score,
                chunk_rank=chunk_rank,
                sentence_index=sentence_index,
            )
            key = " ".join(sentence.lower().split())
            previous = best_by_sentence.get(key)
            if previous is None or candidate.score > previous.score:
                best_by_sentence[key] = candidate

    ranked = sorted(
        best_by_sentence.values(),
        key=lambda candidate: (-candidate.score, candidate.chunk_rank, candidate.sentence_index),
    )

    selected: list[_Candidate] = []
    per_chunk: Counter[int] = Counter()
    best_score = ranked[0].score if ranked else 0.0
    for candidate in ranked:
        if candidate.score <= 0.0:
            continue
        if (
            len(selected) >= _MIN_SENTENCES
            and candidate.score < best_score * _RELATIVE_SCORE_FLOOR
        ):
            break  # remaining sentences are off-topic padding
        if per_chunk[candidate.chunk_rank] >= _MAX_SENTENCES_PER_CHUNK:
            continue
        selected.append(candidate)
        per_chunk[candidate.chunk_rank] += 1
        if len(selected) == _MAX_SENTENCES:
            break

    if len(selected) < _MIN_SENTENCES:  # nothing matched: still say something
        for candidate in ranked:
            if candidate in selected:
                continue
            selected.append(candidate)
            if len(selected) >= min(_MIN_SENTENCES, len(ranked)):
                break

    if not selected:
        fallback = split_sentences(hits[0].chunk.text)
        if fallback:
            return f"{fallback[0]} [1]"
        return _NO_HITS_MESSAGE

    # Chunks stay in retrieval order; inside a chunk the best sentence leads.
    selected.sort(key=lambda candidate: (candidate.chunk_rank, -candidate.score, candidate.sentence_index))
    return " ".join(
        f"{candidate.sentence} [{candidate.chunk_rank + 1}]" for candidate in selected
    )


def _render_sources(hits: list[ScoredChunk]) -> str:
    """Number the retrieved chunks so the model can cite them as [n]."""
    blocks = []
    for rank, hit in enumerate(hits, start=1):
        blocks.append(
            f"[{rank}] ({hit.chunk.source}, {hit.chunk.position})\n{hit.chunk.text}"
        )
    return "\n\n".join(blocks)


def _gemini_answer(question: str, hits: list[ScoredChunk], *, api_key: str | None) -> str:
    """Ask Gemini for a cited answer, then scrub invalid citations."""
    prompt = _ANSWER_PROMPT.format(sources=_render_sources(hits), question=question)
    raw = llm.complete(prompt, system=_ANSWER_SYSTEM)
    return verify_citations(raw, len(hits))


def compose(
    question: str, hits: list[ScoredChunk], *, api_key: str | None = None
) -> tuple[str, str]:
    """Generate an answer from already-retrieved hits; returns (text, mode)."""
    key = api_key if api_key is not None else llm.get_api_key()
    if key and hits:
        try:
            text = _gemini_answer(question, hits, api_key=key)
            if text.strip():
                return text, "gemini"
            logger.warning("Gemini returned only invalid citations — using extractive answer")
        except llm.LLMError as exc:
            logger.warning("generation failed (%s) — using extractive answer", exc)
    return _extractive_answer(question, hits), "extractive"


def answer(
    index: TfidfIndex,
    question: str,
    *,
    k: int = DEFAULT_K,
    min_score: float = 0.0,
    mmr: bool = False,
    mmr_lambda: float = DEFAULT_MMR_LAMBDA,
    api_key: str | None = None,
) -> Answer:
    """Retrieve then generate; latency covers the whole round trip."""
    started = time.perf_counter()
    result = retrieve(
        index,
        question,
        k=k,
        min_score=min_score,
        mmr=mmr,
        mmr_lambda=mmr_lambda,
        api_key=api_key,
    )
    text, mode = compose(question, result.hits, api_key=api_key)
    latency_ms = (time.perf_counter() - started) * 1000.0
    return Answer(text=text, hits=result.hits, latency_ms=latency_ms, mode=mode, queries=result.queries)

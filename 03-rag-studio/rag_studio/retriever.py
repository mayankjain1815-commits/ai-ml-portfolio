"""Retrieve the best chunks: query rewriting, cosine top-k, thresholding, MMR.

The retrieval contract is deliberately small:

1. **Rewrite** the question into a few variants. With a Gemini key, the model
   writes three alternative phrasings; without one, a small thesaurus appends
   synonyms. Rewrites only ever add candidates.
2. **Score** every variant against every chunk by cosine similarity and merge,
   keeping the best score a chunk earned under any phrasing.
3. **Filter** by a minimum score (the default drops non-positive matches).
4. **Pick** either the top k or, with ``--mmr``, a maximal-marginal-relevance
   selection that penalizes chunks too similar to ones already chosen. MMR is
   implemented here by hand over the stored vectors.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from rag_studio import llm
from rag_studio.chunker import Chunk
from rag_studio.index import TfidfIndex, cosine
from rag_studio.thesaurus import expansions

logger = logging.getLogger(__name__)

DEFAULT_K = 5
DEFAULT_MMR_LAMBDA = 0.7  # 1.0 = pure relevance, 0.0 = pure diversity
_MMR_CANDIDATE_MULTIPLIER = 4  # MMR re-ranks a pool, then returns k

_REWRITE_SYSTEM = (
    "You rewrite search queries. Return JSON only, no prose."
)
_REWRITE_PROMPT = """\
Write 3 alternative search queries for the question below. Vary the wording and
include synonyms; do not answer the question. Respond as JSON:
{{"rewrites": ["...", "...", "..."]}}

Question: {question}
"""


@dataclass(frozen=True)
class ScoredChunk:
    """A retrieved chunk and the cosine score that earned it its place."""

    chunk: Chunk
    score: float


@dataclass
class RetrievalResult:
    """Hits plus the query variants that produced them (handy for debugging)."""

    hits: list[ScoredChunk] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)


def expand_query(
    query: str, *, api_key: str | None = None, index: TfidfIndex | None = None
) -> list[str]:
    """Return the original query plus rewritten variants.

    Real mode asks Gemini for three rewrites and falls back to the thesaurus if
    the call or its JSON fails. Demo mode always uses the thesaurus. `index` is
    accepted for API symmetry and future model-aware rewriting.
    """
    del index
    key = api_key if api_key is not None else llm.get_api_key()
    if key:
        try:
            raw = llm.complete(
                _REWRITE_PROMPT.format(question=query),
                system=_REWRITE_SYSTEM,
                json_mode=True,
            )
            rewrites = json.loads(raw).get("rewrites", [])
            variants = [query]
            for variant in rewrites:
                if isinstance(variant, str) and variant.strip() and variant not in variants:
                    variants.append(variant.strip())
            if len(variants) > 1:
                return variants[:4]
            logger.warning("query rewrite returned nothing usable — using thesaurus")
        except (llm.LLMError, ValueError, AttributeError, KeyError) as exc:
            logger.warning("query rewrite failed (%s) — using thesaurus", exc)
    return expansions(query)


def mmr_select(
    candidates: list[ScoredChunk],
    index: TfidfIndex,
    k: int,
    *,
    lambda_: float = DEFAULT_MMR_LAMBDA,
) -> list[ScoredChunk]:
    """Pick k candidates with maximal marginal relevance.

    MMR(d) = lambda * relevance(d, query) - (1 - lambda) * max similarity(d, s)
    over already-selected chunks s. The first pick is always the most relevant;
    every later pick trades a little relevance for novelty. Ties break toward
    the more relevant chunk, then the original order.
    """
    if not candidates:
        return []
    if not 0.0 <= lambda_ <= 1.0:
        raise ValueError("lambda_ must be between 0 and 1")

    remaining = list(candidates)
    selected = [remaining.pop(0)]
    while remaining and len(selected) < k:
        best_index = 0
        best_value = float("-inf")
        for position, candidate in enumerate(remaining):
            relevance = candidate.score
            redundancy = max(
                cosine(index.embedding_of(candidate.chunk.id), index.embedding_of(picked.chunk.id))
                for picked in selected
            )
            value = lambda_ * relevance - (1 - lambda_) * redundancy
            if value > best_value:
                best_index, best_value = position, value
        selected.append(remaining.pop(best_index))
    return selected


def retrieve(
    index: TfidfIndex,
    query: str,
    *,
    k: int = DEFAULT_K,
    min_score: float = 0.0,
    mmr: bool = False,
    mmr_lambda: float = DEFAULT_MMR_LAMBDA,
    api_key: str | None = None,
) -> RetrievalResult:
    """Run the full retrieval pipeline and return the top hits.

    Scores below ``min_score`` are discarded; the default of 0.0 already drops
    chunks with no lexical/semantic overlap with the question, which is almost
    always the right behaviour.
    """
    if k < 1:
        raise ValueError("k must be at least 1")
    queries = expand_query(query, api_key=api_key, index=index)

    best_scores: dict[str, float] = {}
    for variant in queries:
        vector = index.embed_query(variant, api_key=api_key)
        for chunk, score in zip(index.chunks, index.similarities(vector)):
            score = float(score)
            if score > best_scores.get(chunk.id, float("-inf")):
                best_scores[chunk.id] = score

    candidates = [
        ScoredChunk(chunk=chunk, score=best_scores[chunk.id])
        for chunk in index.chunks
        if chunk.id in best_scores and best_scores[chunk.id] > min_score
    ]
    candidates.sort(key=lambda hit: (-hit.score, hit.chunk.id))

    if mmr:
        pool_size = max(k * _MMR_CANDIDATE_MULTIPLIER, k)
        hits = mmr_select(candidates[:pool_size], index, k, lambda_=mmr_lambda)
    else:
        hits = candidates[:k]
    return RetrievalResult(hits=hits, queries=queries)

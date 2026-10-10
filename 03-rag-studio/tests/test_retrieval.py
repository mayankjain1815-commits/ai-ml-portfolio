"""Tests for the TF-IDF index and the retrieval pipeline."""

import numpy as np
import pytest

from rag_studio.chunker import chunk_documents
from rag_studio.index import (
    TfidfIndex,
    build_index,
    cosine,
    load_index,
    save_index,
)
from rag_studio.ingest import document_from_text, load_directory
from rag_studio.retriever import expand_query, mmr_select, retrieve


@pytest.fixture(autouse=True)
def _no_api_key(monkeypatch):
    """Keep every retrieval test hermetic: rewrite must take the thesaurus path."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


# ---------------------------------------------------------------------------
# hand-rolled vector math
# ---------------------------------------------------------------------------


def test_cosine_basics():
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert cosine(a, b) == 0.0
    assert np.isclose(cosine(a, a), 1.0)
    assert np.isclose(cosine(np.array([1.0, 1.0]), np.array([2.0, 2.0])), 1.0)
    # a zero vector has no direction -> 0.0
    assert cosine(np.zeros(2), a) == 0.0


# ---------------------------------------------------------------------------
# building and embedding
# ---------------------------------------------------------------------------

_DOCS = [
    document_from_text("a.md", "The internet routes packets through routers and cables."),
    document_from_text("b.md", "DNS resolves a domain name into an IP address."),
    document_from_text("c.md", "HTTPS encrypts traffic with TLS certificates."),
]


def _small_index():
    chunks = chunk_documents(_DOCS, window=20, overlap=0)
    return build_index(chunks, mode="tfidf")


def test_build_index_normalizes_vectors():
    index = _small_index()
    assert index.mode == "tfidf"
    assert index.vectors.shape == (len(index.chunks), len(index.vocabulary))
    # every row is unit length (unless it is all zeros)
    for row in index.vectors:
        assert np.isclose(np.linalg.norm(row), 1.0)


def test_idf_prefers_rare_terms():
    index = _small_index()
    common_term = "the"  # stopword, not in vocabulary at all
    assert common_term not in index.vocabulary
    # "internet" appears in one doc; rare terms get a higher idf than needed
    rare = index.vocabulary["internet"]
    assert index.idf[rare] > 1.0


def test_embed_query_matches_only_known_terms():
    index = _small_index()
    known = index.embed_tfidf("internet packets")
    unknown = index.embed_tfidf("quantum flurbled widgets")
    assert np.linalg.norm(known) > 0.0
    assert np.linalg.norm(unknown) == 0.0  # all out-of-vocabulary


def test_index_wrong_mode_rejected():
    with pytest.raises(ValueError):
        TfidfIndex(
            chunks=[], vectors=np.zeros((0, 0)), vocabulary={}, idf=np.zeros(0), mode="wacky"
        )


# ---------------------------------------------------------------------------
# persistence
# ---------------------------------------------------------------------------


def test_save_load_round_trip(tmp_path):
    index = _small_index()
    save_index(index, tmp_path)
    loaded = load_index(tmp_path)
    assert loaded.mode == "tfidf"
    assert [c.id for c in loaded.chunks] == [c.id for c in index.chunks]
    assert loaded.vocabulary == index.vocabulary
    assert np.array_equal(loaded.vectors, index.vectors)
    assert np.array_equal(loaded.idf, index.idf)


def test_load_missing_index_has_remedy(tmp_path):
    with pytest.raises(FileNotFoundError, match="build one first"):
        load_index(tmp_path / "nope")


def test_load_unsupported_format_rejected(tmp_path):
    index = _small_index()
    save_index(index, tmp_path)
    meta_path = tmp_path / "meta.json"
    import json

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["format_version"] = 99
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(ValueError, match="not supported"):
        load_index(tmp_path)


# ---------------------------------------------------------------------------
# retrieval
# ---------------------------------------------------------------------------


def test_retrieve_ranks_relevant_chunk_first():
    index = _small_index()
    result = retrieve(index, "how does dns resolve a domain name", k=3)
    assert result.hits
    assert result.hits[0].chunk.source == "b.md"
    # scores are descending
    scores = [hit.score for hit in result.hits]
    assert scores == sorted(scores, reverse=True)


def test_retrieve_respects_min_score():
    index = _small_index()
    all_hits = retrieve(index, "internet packets routers", k=3, min_score=0.0)
    strict = retrieve(index, "internet packets routers", k=3, min_score=0.1)
    assert len(strict.hits) <= len(all_hits.hits)


def test_retrieve_k_must_be_positive():
    index = _small_index()
    with pytest.raises(ValueError, match="k must be at least 1"):
        retrieve(index, "anything", k=0)


def test_retrieve_offline_expands_query_through_thesaurus():
    index = _small_index()
    result = retrieve(index, "how does dns work", k=2)
    # offline mode: thesaurus expansion adds variants, never fewer than one
    variants = result.queries
    assert len(variants) >= 1
    assert variants[0] == "how does dns work"


def test_mmr_pure_relevance_matches_plain_top_k():
    index = _small_index()
    plain = retrieve(index, "internet packets routers cables", k=2, mmr=False)
    mmr_rel = retrieve(
        index, "internet packets routers cables", k=2, mmr=True, mmr_lambda=1.0
    )
    assert [h.chunk.id for h in mmr_rel.hits] == [h.chunk.id for h in plain.hits]


def test_mmr_diversity_changes_selection():
    index = _small_index()
    # two near-duplicate chunks vs one distinct chunk: pure diversity avoids the twins
    docs = [
        document_from_text("x.md", "Routers forward packets between cables and networks."),
        document_from_text("y.md", "Routers forward packets between cables and networks too."),
        # distinct topic, but one shared query term so it survives the min_score filter
        document_from_text("z.md", "Packets carry data while DNS maps domain names to resolvers."),
    ]
    chunks = chunk_documents(docs, window=12, overlap=0)
    idx = build_index(chunks, mode="tfidf")
    candidates = retrieve(idx, "routers forward packets", k=5).hits
    selected_rel = mmr_select(candidates, idx, 2, lambda_=1.0)
    selected_div = mmr_select(candidates, idx, 2, lambda_=0.0)
    assert {c.chunk.id for c in selected_div} != {c.chunk.id for c in selected_rel}


def test_mmr_lambda_out_of_range():
    index = _small_index()
    candidates = retrieve(index, "internet packets routers", k=3).hits
    with pytest.raises(ValueError, match="lambda_"):
        mmr_select(candidates, index, 2, lambda_=1.5)


def test_expand_query_thesaurus_when_no_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    variants = expand_query("what is dns", api_key=None)
    assert isinstance(variants, list) and len(variants) >= 1


# ---------------------------------------------------------------------------
# bundled-corpus integration: the real docs answer real questions
# ---------------------------------------------------------------------------


def test_bundled_docs_retrieve_gold_source():
    from rag_studio.evals import harness

    documents = load_directory(_bundled_docs_dir())
    chunks = chunk_documents(documents)
    index = build_index(chunks, mode="tfidf")
    questions = harness.load_questions()
    question = questions[0]  # "Why does the internet split data into packets..."
    result = retrieve(index, question.question, k=5)
    ranks = [hit.chunk.source for hit in result.hits]
    assert question.source in ranks


def _bundled_docs_dir():
    from pathlib import Path

    return Path(__file__).resolve().parents[1] / "data" / "docs"
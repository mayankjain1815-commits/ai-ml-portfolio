"""Hand-rolled TF-IDF index, optional Gemini embeddings, and JSON+npz persistence.

The vectorizer is written from scratch on purpose: term frequencies, smoothed
inverse document frequencies, L2 normalization and cosine similarity are all a
few lines of numpy, and seeing them makes retrieval debuggable in a way a
library call is not.

Two interchangeable modes sit behind the same interface:

* ``tfidf``  — lexical matching, fully offline and deterministic (the default);
* ``gemini`` — dense embeddings from the Gemini REST API, enabled by setting
  ``GEMINI_API_KEY``.

Whichever mode built the index is recorded in ``meta.json``; queries must be
embedded the same way, so loading a gemini index without a key fails with a
pointer to rebuild using TF-IDF.

On disk an index is two files inside a directory:

    index/meta.json     format version, mode, chunk list, vocabulary, settings
    index/vectors.npz   the (chunks x terms) L2-normalized matrix and idf vector
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from rag_studio import llm
from rag_studio.chunker import Chunk
from rag_studio.text import tokenize

FORMAT_VERSION = 1
MODES = ("tfidf", "gemini")


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors, 0.0 when either is all zeros."""
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _l2_normalize(vector: np.ndarray) -> np.ndarray:
    """Scale a vector to unit length; all-zero vectors are returned unchanged."""
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        return vector
    return vector / norm


def _smoothed_idf(document_frequency: int, n_documents: int) -> float:
    """ln((1 + N) / (1 + df)) + 1 — the classic smoothed inverse document frequency.

    The +1 pieces keep terms that appear in every document from collapsing to
    zero and avoid division by zero for a term nobody uses.
    """
    return float(np.log((1 + n_documents) / (1 + document_frequency)) + 1.0)


@dataclass
class TfidfIndex:
    """A vector store over chunks plus the vocabulary/statistics to query it."""

    chunks: list[Chunk]
    vectors: np.ndarray  # (len(chunks), n_terms); rows are L2-normalized
    vocabulary: dict[str, int]  # term -> column (empty in gemini mode)
    idf: np.ndarray  # (n_terms,) (empty in gemini mode)
    mode: str = "tfidf"
    created_at: str = ""
    meta: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(f"unknown index mode {self.mode!r}; expected one of {MODES}")
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self._rows: dict[str, int] = {chunk.id: row for row, chunk in enumerate(self.chunks)}

    # -- vectorizing -------------------------------------------------------

    def embed_tfidf(self, text: str) -> np.ndarray:
        """Embed text with the stored vocabulary and idf (out-of-vocab terms are
        silently dropped, which is why an unknown query scores zero)."""
        vector = np.zeros(len(self.idf), dtype=np.float64)
        for term, frequency in Counter(tokenize(text)).items():
            column = self.vocabulary.get(term)
            if column is not None:
                vector[column] = frequency * self.idf[column]
        return _l2_normalize(vector)

    def embed_query(self, text: str, *, api_key: str | None = None) -> np.ndarray:
        """Embed a query with the same mode the index was built in."""
        if self.mode == "gemini":
            vectors = llm.embed_texts([text], api_key=api_key)
            return _l2_normalize(np.asarray(vectors[0], dtype=np.float64))
        return self.embed_tfidf(text)

    def similarities(self, query_vector: np.ndarray) -> np.ndarray:
        """Cosine similarity of every chunk against a query vector.

        Rows are L2-normalized at build time, so the dot product *is* the
        cosine; the query vector is normalized by embed_query.
        """
        if not self.chunks:
            return np.zeros(0, dtype=np.float64)
        return self.vectors @ query_vector

    def embedding_of(self, chunk_id: str) -> np.ndarray:
        """Vector for a chunk id — used by MMR to compare candidates."""
        return self.vectors[self._rows[chunk_id]]


def build_index(
    chunks: list[Chunk],
    *,
    mode: str = "tfidf",
    api_key: str | None = None,
) -> TfidfIndex:
    """Build an index over `chunks` in the requested mode.

    In gemini mode the embeddings are produced in one batch call; any failure
    raises llm.LLMError with the rebuild-without-a-key remedy (no silent mixing
    of embedding spaces).
    """
    if mode not in MODES:
        raise ValueError(f"unknown index mode {mode!r}; expected one of {MODES}")

    if mode == "gemini":
        raw = llm.embed_texts([chunk.text for chunk in chunks], api_key=api_key)
        vectors = np.asarray(raw, dtype=np.float64) if raw else np.zeros((0, 0))
        if len(chunks):
            vectors = np.vstack([_l2_normalize(row) for row in vectors])
        return TfidfIndex(
            chunks=list(chunks),
            vectors=vectors,
            vocabulary={},
            idf=np.zeros(0, dtype=np.float64),
            mode="gemini",
            meta={"chunk_count": len(chunks)},
        )

    tokenized = [tokenize(chunk.text) for chunk in chunks]
    document_frequency: Counter[str] = Counter()
    for tokens in tokenized:
        document_frequency.update(set(tokens))
    vocabulary = {term: column for column, term in enumerate(sorted(document_frequency))}
    idf = np.zeros(len(vocabulary), dtype=np.float64)
    n_documents = len(chunks) or 1
    for term, column in vocabulary.items():
        idf[column] = _smoothed_idf(document_frequency[term], n_documents)

    vectors = np.zeros((len(chunks), len(vocabulary)), dtype=np.float64)
    for row, tokens in enumerate(tokenized):
        for term, frequency in Counter(tokens).items():
            vectors[row, vocabulary[term]] = frequency * idf[vocabulary[term]]
        vectors[row] = _l2_normalize(vectors[row])
    return TfidfIndex(
        chunks=list(chunks),
        vectors=vectors,
        vocabulary=vocabulary,
        idf=idf,
        mode="tfidf",
        meta={"chunk_count": len(chunks), "vocabulary_size": len(vocabulary)},
    )


# -- persistence -----------------------------------------------------------


def save_index(index: TfidfIndex, directory: str | Path) -> Path:
    """Write `meta.json` and `vectors.npz` into `directory`."""
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    meta = {
        "format_version": FORMAT_VERSION,
        "mode": index.mode,
        "created_at": index.created_at,
        "vocabulary": sorted(index.vocabulary, key=index.vocabulary.get),
        "settings": index.meta,
        "chunks": [
            {
                "id": chunk.id,
                "text": chunk.text,
                "source": chunk.source,
                "position": chunk.position,
                "start": chunk.start,
                "end": chunk.end,
            }
            for chunk in index.chunks
        ],
    }
    (path / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    np.savez_compressed(path / "vectors.npz", vectors=index.vectors, idf=index.idf)
    return path


def load_index(directory: str | Path) -> TfidfIndex:
    """Load a previously saved index; raises FileNotFoundError with the remedy."""
    path = Path(directory)
    meta_path = path / "meta.json"
    vectors_path = path / "vectors.npz"
    if not meta_path.is_file() or not vectors_path.is_file():
        raise FileNotFoundError(
            f"no index found in {path} — build one first with "
            "'python -m rag_studio build data/docs'"
        )
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("format_version") != FORMAT_VERSION:
        raise ValueError(
            f"index format v{meta.get('format_version')} is not supported "
            f"(expected v{FORMAT_VERSION}) — rebuild the index"
        )
    with np.load(vectors_path, allow_pickle=False) as data:
        vectors = data["vectors"]
        idf = data["idf"]
    vocabulary = {term: column for column, term in enumerate(meta["vocabulary"])}
    chunks = [Chunk(**entry) for entry in meta["chunks"]]
    return TfidfIndex(
        chunks=chunks,
        vectors=vectors,
        vocabulary=vocabulary,
        idf=idf,
        mode=meta["mode"],
        created_at=meta.get("created_at", ""),
        meta=meta.get("settings", {}),
    )

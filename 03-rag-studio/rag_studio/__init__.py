"""RAG Studio — a from-scratch retrieval-augmented generation pipeline.

The package is deliberately layered so every stage of a RAG system is a small,
testable module:

    ingest -> chunker -> index -> retriever -> generate -> evals

No langchain, no llama-index: the vectorizer, the MMR formula, the metrics and
the eval harness are all implemented here by hand.
"""

__version__ = "1.0.0"

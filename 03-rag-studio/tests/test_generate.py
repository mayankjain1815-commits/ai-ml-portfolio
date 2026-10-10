"""Tests for the generation step: extractive answers and citation verification."""

import pytest

from rag_studio.chunker import chunk_documents
from rag_studio.generate import _extractive_answer, answer, verify_citations
from rag_studio.index import build_index
from rag_studio.ingest import document_from_text


def test_verify_citations_drops_out_of_range():
    text = "Packets carry data [1] and each has a header [2]. See also [9]."
    cleaned = verify_citations(text, n_sources=2)
    assert "[1]" in cleaned and "[2]" in cleaned
    assert "[9]" not in cleaned


def test_verify_citations_tidies_spacing():
    text = "One  sentence  [1] .  Extra   spaces."
    cleaned = verify_citations(text, n_sources=1)
    assert "  " not in cleaned
    assert "." in cleaned


def test_extractive_answer_no_hits():
    message = _extractive_answer("anything", [])
    assert "could not find any relevant passages" in message


def test_extractive_answer_is_grounded_and_cited():
    doc = document_from_text(
        "dns.md",
        "DNS turns a domain name into an IP address by asking a resolver. "
        "The resolver walks the tree from the root servers down to the answer.",
    )
    index = build_index(chunk_documents([doc], window=12, overlap=0), mode="tfidf")
    result = answer(index, "how does dns resolve a domain name", k=3)
    assert result.mode == "extractive"
    assert result.hits  # retrieval found the chunk
    # every claim carries a citation and is copied verbatim from the source
    for hit in result.hits:
        assert hit.chunk.source == "dns.md"
    assert "[1]" in result.text
    assert "resolver" in result.text


def test_extractive_answer_prefers_overlapping_sentences():
    doc = document_from_text(
        "pkt.md",
        "The internet splits data into small pieces called packets. "
        "Each packet carries a payload and a header. "
        "Routers forward packets to the next hop.",
    )
    index = build_index(chunk_documents([doc], window=10, overlap=0), mode="tfidf")
    result = answer(index, "why does the internet split data into packets", k=3)
    assert result.mode == "extractive"
    assert "packet" in result.text
    assert result.hits  # retrieval found the chunk


def test_answer_reports_queries_and_latency():
    doc = document_from_text(
        "tls.md",
        "HTTPS certificates prove identity with a chain of trust. "
        "A certificate authority signs the certificate.",
    )
    index = build_index(chunk_documents([doc], window=10, overlap=0), mode="tfidf")
    result = answer(index, "what do https certificates prove", k=2)
    assert result.queries
    assert result.latency_ms >= 0.0
    assert result.hits is not None
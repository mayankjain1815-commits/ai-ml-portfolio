"""Tests for thesaurus query expansion and the offline llm fallback."""

import json

import pytest

from rag_studio import llm
from rag_studio.thesaurus import THESAURUS, expansions


def test_expansions_no_match_returns_original():
    assert expansions("flurbled widgets") == ["flurbled widgets"]


def test_expansions_adds_synonyms():
    variants = expansions("what is dns")
    assert variants[0] == "what is dns"
    assert len(variants) == 2
    expanded = variants[1].lower()
    assert "resolver" in expanded or "domain name" in expanded or "lookup" in expanded


def test_expansions_deduplicates():
    # "web website" would otherwise expand into overlapping synonym sets
    variants = expansions("web website")
    assert len(variants) == 2
    assert variants[1].count("site") <= 2


def test_thesaurus_keys_are_normalized():
    # every table key must be what the tokenizer would produce, or it can never fire
    from rag_studio.text import tokenize

    for key in THESAURUS:
        assert tokenize(key) == [key]


def test_offline_complete_json_mode_returns_rewrites():
    raw = llm._offline_complete("Question: what is dns", json_mode=True)
    payload = json.loads(raw)
    assert isinstance(payload["rewrites"], list)
    assert payload["rewrites"]


def test_offline_complete_pulls_sentences_from_sources():
    prompt = (
        "Sources:\n[1] (dns.md, line 1)\n"
        "DNS turns a domain name into an IP address using a resolver.\n"
        "The resolver walks from the root servers down to the answer.\n"
        "\nQuestion: how does dns work\n\nAnswer:"
    )
    text = llm._offline_complete(prompt)
    assert "resolver" in text.lower()
    assert text.strip()


def test_get_api_key_none_without_env(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert llm.get_api_key() is None


def test_complete_without_key_uses_offline_generator(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    prompt = (
        "Sources:\n[1] (dns.md, line 1)\n"
        "DNS turns a domain name into an IP address using a resolver.\n"
        "The resolver walks from the root servers down to the answer.\n"
        "\nQuestion: how does dns work\n\nAnswer:"
    )
    text = llm.complete(prompt)
    assert text.strip()
    assert "resolver" in text.lower()


def test_embed_texts_requires_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(llm.LLMError):
        llm.embed_texts(["hello"])
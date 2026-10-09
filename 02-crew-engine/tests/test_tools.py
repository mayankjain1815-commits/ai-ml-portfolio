"""Tests for the tool registry and bundled corpus."""

import pytest

from crew_engine.tools import (
    Tool,
    ToolRegistry,
    corpus_search,
    default_registry,
    load_corpus,
    read_doc,
)


def test_corpus_is_bundled_and_nonempty():
    docs = load_corpus()
    assert docs, "corpus must ship with the project"
    for name, text in docs.items():
        assert len(text) > 500, f"{name} looks too short to be useful"
    assert "readme" not in {d.lower() for d in docs}


def test_corpus_search_returns_scored_citations():
    out = corpus_search("neural network learning", k=3)
    assert out.startswith("corpus_search")
    assert "[source:" in out
    # top hits come from the document about neural networks
    first = out.splitlines()[1]
    assert "neural-networks" in first or "ai-in-the-world" in first


def test_corpus_search_handles_stopword_only_query():
    out = corpus_search("the and of for")
    assert "no content words" in out


def test_corpus_search_handles_empty_query():
    out = corpus_search("   ")
    assert "no content words" in out


def test_read_doc_known():
    text = read_doc("history-of-ai")
    assert "history-of-ai" in text
    assert len(text) > 500


def test_read_doc_unknown_lists_known():
    out = read_doc("nope")
    assert "unknown doc" in out
    assert "history-of-ai" in out


def test_registry_duplicate_rejected():
    reg = ToolRegistry()
    reg.register(Tool("a", "first", lambda: "1"))
    with pytest.raises(ValueError):
        reg.register(Tool("a", "second", lambda: "2"))


def test_registry_missing_tool_message():
    reg = ToolRegistry()
    with pytest.raises(KeyError) as exc:
        reg.get("ghost")
    assert "no tool named" in str(exc.value)


def test_default_registry_has_all_tools():
    reg = default_registry()
    assert {"corpus_search", "read_doc", "web_search", "now", "save_artifact"} <= set(
        reg.tools
    )
    desc = reg.descriptions()
    for name in reg.tools:
        assert f"- {name}:" in desc


def test_save_artifact_writes_file(tmp_path, monkeypatch):
    import crew_engine.tools as tools

    monkeypatch.setattr(tools, "ARTIFACTS_DIR", tmp_path)
    result = tools.save_artifact("demo note", "hello world")
    assert "save_artifact: wrote 11 chars to" in result
    assert (tmp_path / "demo_note.txt").read_text() == "hello world"
    # unsafe characters are sanitized out of the file name
    tools.save_artifact("a/b:c", "x")
    assert "a_b_c.txt" in {p.name for p in tmp_path.iterdir()}
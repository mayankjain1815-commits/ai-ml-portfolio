"""Tests for the boundary-aware word-window chunker."""

import pytest

from rag_studio.chunker import (
    chunk_document,
    chunk_documents,
    is_line_boundary,
    is_paragraph_boundary,
    is_sentence_boundary,
    score_cut,
)
from rag_studio.ingest import document_from_text


def _doc(text: str, source: str = "test.md"):
    return document_from_text(source, text)


def test_empty_document_yields_no_chunks():
    assert chunk_document(_doc("")) == []
    assert chunk_document(_doc("   \n \n")) == []


def test_short_document_is_one_chunk():
    text = "Packets carry data across the network in small pieces."
    chunks = chunk_document(_doc(text), window=400)
    assert len(chunks) == 1
    assert chunks[0].text == text
    assert chunks[0].source == "test.md"
    assert chunks[0].id == "test.md:001"
    assert chunks[0].start == 0
    assert chunks[0].end == len(text)


def test_multi_chunk_ids_and_overlap():
    text = " ".join(f"word{i}" for i in range(120))
    chunks = chunk_document(_doc(text), window=50, overlap=10)
    assert len(chunks) >= 2
    assert [c.id for c in chunks] == [
        f"test.md:{i:03d}" for i in range(1, len(chunks) + 1)
    ]
    # the next window starts before the previous one ended -> overlap region exists
    assert chunks[1].start < chunks[0].end
    assert all(c.position for c in chunks)


def test_chunks_cover_the_document():
    text = " ".join(f"word{i}" for i in range(150))
    chunks = chunk_document(_doc(text), window=60, overlap=20)
    assert chunks[0].start == 0
    assert chunks[0].text.startswith("word0")
    assert chunks[-1].end == len(text)
    assert chunks[-1].text.endswith("word149")


def test_remainder_smaller_than_overlap_is_absorbed():
    # 30 words with a 400-word window: never split, absorbed whole
    text = " ".join(f"word{i}" for i in range(30))
    chunks = chunk_document(_doc(text), window=400, overlap=40)
    assert len(chunks) == 1
    assert chunks[0].text == text


def test_window_and_overlap_validation():
    with pytest.raises(ValueError):
        chunk_document(_doc("hello world"), window=0)
    with pytest.raises(ValueError):
        chunk_document(_doc("hello world"), window=10, overlap=10)
    with pytest.raises(ValueError):
        chunk_document(_doc("hello world"), window=10, overlap=11)


def test_sentence_boundary_detection():
    text = "One sentence here. Second sentence here.\nAnother block."
    after_first = text.index(". ") + 1  # offset of the space after "here."
    assert is_sentence_boundary(text, after_first) is True
    # mid-word is never a boundary
    assert is_sentence_boundary(text, 3) is False
    # an abbreviation like e.g. must not be treated as a sentence end
    abbr = "We use e.g. TCP for delivery."
    assert is_sentence_boundary(abbr, abbr.index(" TCP")) is False
    # end of text counts as a boundary
    assert is_sentence_boundary("The end.", len("The end.")) is True


def test_paragraph_and_line_boundaries():
    text = "First paragraph.\n\nSecond paragraph."
    at_blank = text.index("\n\n")
    assert is_paragraph_boundary(text, at_blank) is True
    assert is_line_boundary(text, at_blank) is True

    soft = "a list item without punctuation\nsecond item"
    at_newline = soft.index("\n")
    assert is_line_boundary(soft, at_newline) is True
    assert is_paragraph_boundary(soft, at_newline) is False


def test_score_cut_prefers_stronger_boundaries():
    paragraph = "Sentence one here.\n\nSentence two here."
    sentence = "Sentence one here. Sentence two here."
    line = "a line without punctuation\nnext line"
    mid = "just some words here with no boundary at all"
    # compare at zero distance so only boundary kind matters
    assert score_cut(paragraph, paragraph.index("\n\n"), 0) > score_cut(
        sentence, sentence.index(". ") + 1, 0
    )
    assert score_cut(sentence, sentence.index(". ") + 1, 0) > score_cut(
        line, line.index("\n"), 0
    )
    assert score_cut(line, line.index("\n"), 0) > score_cut(mid, mid.index(" words"), 0)


def test_chunk_documents_concatenates_in_order():
    a = _doc("alpha " * 30, source="a.md")
    b = _doc("beta " * 30, source="b.md")
    chunks = chunk_documents([a, b], window=25, overlap=5)
    sources = {c.source for c in chunks}
    assert sources == {"a.md", "b.md"}
    # chunk ids are per-document, both starting at 001
    assert [c.id for c in chunks if c.source == "a.md"][0] == "a.md:001"
    assert [c.id for c in chunks if c.source == "b.md"][0] == "b.md:001"
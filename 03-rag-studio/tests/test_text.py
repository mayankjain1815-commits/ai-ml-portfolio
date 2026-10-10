"""Tests for the text primitives: tokenization and sentence splitting."""

from rag_studio.text import content_words, split_sentences, tokenize


def test_tokenize_case_folds_and_splits():
    assert tokenize("The Packets arrive!") == ["packet", "arrive"]
    assert tokenize("Café") == ["cafe"]  # diacritics folded away: é -> e


def test_tokenize_drops_stopwords_and_short_tokens():
    tokens = tokenize("why does the internet use packets")
    assert "why" not in tokens and "the" not in tokens and "does" not in tokens
    assert "internet" in tokens and "packet" in tokens


def test_tokenize_singularizes_plurals():
    assert tokenize("packets routers protocols") == ["packet", "router", "protocol"]
    # "ss" endings are not pluralized: "address" stays "address"
    assert "address" in tokenize("the address")


def test_tokenize_keeps_digits_and_drops_punct():
    assert "404" in tokenize("a 404 error")
    # apostrophe splits into two tokens; the "t" is dropped as too short
    assert tokenize("don't stop") == ["don", "stop"]


def test_tokenize_drops_len_one_tokens():
    assert "a" not in tokenize("a b c")


def test_content_words_is_unique_set():
    words = content_words("packet packet packet router")
    assert words == {"packet", "router"}


def test_split_sentences_basic():
    text = "The internet uses packets. Packets have headers. Do they route?"
    assert split_sentences(text) == [
        "The internet uses packets.",
        "Packets have headers.",
        "Do they route?",
    ]


def test_split_sentences_strips_and_drops_blanks():
    assert split_sentences("  one.   two!\n\nthree?  ") == ["one.", "two!", "three?"]


def test_split_sentences_single():
    assert split_sentences("just one sentence.") == ["just one sentence."]
    assert split_sentences("no punctuation") == ["no punctuation"]
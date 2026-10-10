"""Text primitives shared by the vectorizer, the metrics, and the demo generator.

One tokenizer lives here so that indexing, query embedding, and the
faithfulness metric all agree on what a "content word" is. The normalization is
intentionally small and inspectable:

* case-fold and strip diacritics (NFKD decompose, drop combining marks; so
  "Café" and "cafe" match),
* keep alphanumeric tokens only (so "404" survives, "don't" becomes two tokens),
* drop a compact English stopword list (so "why does the" never drives scores),
* strip one trailing "s" from long words ("packets" -> "packet"), except
  "ss"/"us"/"is" endings that are not plurals. The rule is crude but
  consistent, and consistency is all TF-IDF needs to match terms.
"""

from __future__ import annotations

import re
import unicodedata

STOPWORDS = frozenset(
    """
    a about after again all also am an and any are as at be because been before
    being both but by can could did do does doing down during each few for from
    further had has have having he her here hers herself him himself his how i
    if in into its itself just me more most my myself no nor not of off on once
    only or other our ours ourselves out over own same she should so some such
    than that the their theirs them themselves then there these they this those
    through to too under until up very was we were what when where which while
    who whom why will with would you your yours yourself yourselves
    """.split()
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def normalize_token(token: str) -> str | None:
    """Normalize one raw token; return None when it carries no signal."""
    if len(token) <= 1 or token in STOPWORDS:
        return None
    if (
        len(token) > 3
        and token.endswith("s")
        and not token.endswith(("ss", "us", "is"))  # address, status, basis aren't plurals
    ):
        token = token[:-1]
    return token


def _fold(text: str) -> str:
    """Case-fold and strip diacritics so "Café" and "cafe" match."""
    decomposed = unicodedata.normalize("NFKD", text).lower()
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def tokenize(text: str) -> list[str]:
    """Split text into normalized content tokens, in order of appearance."""
    tokens = []
    for raw in _TOKEN_RE.findall(_fold(text)):
        token = normalize_token(raw)
        if token is not None:
            tokens.append(token)
    return tokens


def content_words(text: str) -> set[str]:
    """Unique content tokens of `text` — the unit both metrics compare on."""
    return set(tokenize(text))


def split_sentences(text: str) -> list[str]:
    """Split prose into sentences on punctuation followed by whitespace.

    Deliberately regex-based rather than NLP-grade: it only needs to be good
    enough to pick quotable sentences out of already-clean document text.
    """
    return [part.strip() for part in _SENTENCE_RE.split(text.strip()) if part.strip()]

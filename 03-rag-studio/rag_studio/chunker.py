"""Word-window chunking that prefers to cut at paragraph or sentence boundaries.

The window is measured in words (default 400 with 80 words of overlap), but a
blind fixed-size window happily slices a sentence in half, which produces
contextless half-answers and ugly citations. So every candidate cut inside a
search band around the target gets scored: paragraph breaks win, sentence ends
next, line ends slightly, and a mid-sentence cut is heavily penalized. Ties in
kind are broken by distance from the target so chunks stay close to the requested
size.

Overlap exists because a fact straddling a cut must be visible whole in at least
one chunk; the next window therefore starts `overlap` words before the previous
one ended. When the remainder of a document would be smaller than the overlap,
it is absorbed instead of producing a near-duplicate tail chunk, so chunk sizes
stay within [roughly window - band, window + overlap].
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rag_studio.ingest import Document

DEFAULT_WINDOW = 400  # words per chunk
DEFAULT_OVERLAP = 80  # words repeated at the start of the next chunk

_PARAGRAPH_BONUS = 4.0
_SENTENCE_BONUS = 2.0
_LINE_BONUS = 1.0
_MID_SENTENCE_PENALTY = 6.0
_DISTANCE_PENALTY = 0.01  # score lost per word of distance from the target cut

_WORD_RE = re.compile(r"\S+")
_SENTENCE_END = ".?!"
_CLOSERS = "\"')]”’»"
_ABBREVIATION_RE = re.compile(r"(?:[A-Za-z]\.)+")


@dataclass(frozen=True)
class Chunk:
    """One retrieval unit with full provenance back to its source file."""

    id: str  # "<source>:<per-doc ordinal>", e.g. "02-dns.md:001"
    text: str
    source: str  # file name the chunk came from
    position: str  # human label, e.g. "lines 14-31" or "page 2"
    start: int  # character offset of the chunk start in the source document
    end: int  # character offset of the chunk end in the source document


def is_sentence_boundary(text: str, pos: int) -> bool:
    """True when character offset `pos` sits right after a complete sentence.

    End of text counts as a boundary, closing quotes/brackets are skipped, and
    abbreviations such as "e.g." are rejected so they don't earn the bonus and
    lure the chunker into a mid-sentence cut.
    """
    if pos <= 0 or pos > len(text):
        return False
    if not text[pos:].strip():
        return True  # only whitespace follows: the text ends here
    if not text[pos].isspace():
        return False  # not a word boundary, so not a sentence boundary
    scan = pos
    while scan > 0 and text[scan - 1] in _CLOSERS:
        scan -= 1
    if scan == 0 or text[scan - 1] not in _SENTENCE_END:
        return False
    word_start = max(text.rfind(" ", 0, scan), text.rfind("\n", 0, scan)) + 1
    word = text[word_start:scan]
    return _ABBREVIATION_RE.fullmatch(word) is None


def is_paragraph_boundary(text: str, pos: int) -> bool:
    """True when a blank line follows `pos` — the strongest place to cut."""
    return re.match(r"[ \t]*\n[ \t]*\n", text[pos:]) is not None


def is_line_boundary(text: str, pos: int) -> bool:
    """True when `pos` ends a line (soft-wrap or list item)."""
    return re.match(r"[ \t]*\n", text[pos:]) is not None


def score_cut(text: str, cut_char: int, distance: int) -> float:
    """Score a candidate cut position; higher is better.

    `distance` is how many words the cut sits away from the ideal target end of
    the window. Boundary quality dominates, then closeness to the target breaks
    near-ties, which keeps chunks within a search band of the requested size.
    """
    if is_paragraph_boundary(text, cut_char):
        base = _PARAGRAPH_BONUS
    elif is_sentence_boundary(text, cut_char):
        base = _SENTENCE_BONUS
    elif is_line_boundary(text, cut_char):
        base = _LINE_BONUS
    else:
        base = -_MID_SENTENCE_PENALTY
    return base - _DISTANCE_PENALTY * distance


def chunk_document(
    document: Document, *, window: int = DEFAULT_WINDOW, overlap: int = DEFAULT_OVERLAP
) -> list[Chunk]:
    """Split a document into overlapping word windows with provenance labels.

    Returns an empty list for empty/whitespace-only documents and exactly one
    chunk when the document fits inside `window + overlap` words (a document
    shorter than the window is never split).
    """
    if window < 1:
        raise ValueError("window must be at least 1 word")
    if not 0 <= overlap < window:
        raise ValueError("overlap must be between 0 and window - 1")

    words = [(match.start(), match.end()) for match in _WORD_RE.finditer(document.text)]
    count = len(words)
    if count == 0:
        return []

    ranges: list[tuple[int, int]] = []  # (start word index, end word index exclusive)
    start = 0
    while True:
        if count - start <= window + overlap:
            if start < count:  # absorb the remainder; nothing left when start == count
                ranges.append((start, count))
            break
        target = start + window
        band = max(10, window // 5)
        low = max(start + 1, target - band)
        high = min(count, target + band)

        best_index, best_score, best_distance = target, float("-inf"), 0
        for index in range(low, high + 1):
            cut_char = words[index - 1][1]
            distance = abs(index - target)
            score = score_cut(document.text, cut_char, distance)
            if score > best_score or (score == best_score and distance < best_distance):
                best_index, best_score, best_distance = index, score, distance

        ranges.append((start, best_index))
        start = max(best_index - overlap, start + 1)  # strict progress, always

    chunks = []
    for ordinal, (first_word, last_word) in enumerate(ranges, start=1):
        char_start = words[first_word][0]
        char_end = words[last_word - 1][1]
        chunks.append(
            Chunk(
                id=f"{document.source}:{ordinal:03d}",
                text=document.text[char_start:char_end],
                source=document.source,
                position=document.locator_for(char_start, char_end),
                start=char_start,
                end=char_end,
            )
        )
    return chunks


def chunk_documents(
    documents: list[Document], *, window: int = DEFAULT_WINDOW, overlap: int = DEFAULT_OVERLAP
) -> list[Chunk]:
    """Chunk every document in order; empty documents contribute nothing."""
    chunks: list[Chunk] = []
    for document in documents:
        chunks.extend(chunk_document(document, window=window, overlap=overlap))
    return chunks

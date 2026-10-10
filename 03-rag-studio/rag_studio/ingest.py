"""Load .txt, .md, and .pdf files while remembering where every character came from.

Provenance is the point of this module. A chunk that gets cited in an answer can
point back to "02-dns.md (lines 14-31)" or "guide.pdf (pages 1-2)" because every
Document carries a span map from character offsets to line/page numbers, and the
chunker asks that map for the slice it cut.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = (".txt", ".md", ".markdown", ".pdf")


@dataclass(frozen=True)
class Span:
    """A run of document text that maps to one locator (a single line or page)."""

    start: int  # inclusive character offset in Document.text
    end: int  # exclusive character offset in Document.text
    kind: str  # "line" for text files, "page" for PDFs
    number: int  # 1-based line/page number


@dataclass(frozen=True)
class Document:
    """One source file plus the offset -> line/page map for its text."""

    source: str  # file name, e.g. "02-dns-and-websites.md"
    text: str
    spans: tuple[Span, ...]

    def locator_for(self, start: int, end: int) -> str:
        """Return a human-readable provenance label for the [start, end) slice.

        Consecutive lines/pages collapse into ranges, so a cut spanning lines
        14 through 31 reports "lines 14-31" instead of eighteen labels.
        """
        overlapping = [span for span in self.spans if span.start < end and span.end > start]
        if not overlapping:
            return "text"
        numbers = sorted({span.number for span in overlapping})
        runs: list[tuple[int, int]] = []
        run_start = previous = numbers[0]
        for number in numbers[1:]:
            if number == previous + 1:
                previous = number
                continue
            runs.append((run_start, previous))
            run_start = previous = number
        runs.append((run_start, previous))

        inner = ", ".join(str(lo) if lo == hi else f"{lo}-{hi}" for lo, hi in runs)
        if len(runs) == 1 and runs[0][0] == runs[0][1]:
            return f"{overlapping[0].kind} {inner}"
        return f"{overlapping[0].kind}s {inner}"


def line_spans(text: str) -> tuple[Span, ...]:
    """Build the span map for plain text: one span per 1-based line number."""
    spans: list[Span] = []
    offset = 0
    for number, line in enumerate(text.splitlines(keepends=True), start=1):
        spans.append(Span(offset, offset + len(line), "line", number))
        offset += len(line)
    return tuple(spans)


def document_from_text(source: str, text: str) -> Document:
    """Wrap raw text in a Document with line spans (used by tests and callers
    that already hold text in memory)."""
    return Document(source=source, text=text, spans=line_spans(text))


def load_file(path: str | Path) -> Document:
    """Load a single supported file, preserving its filename as the source."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in (".txt", ".md", ".markdown"):
        text = path.read_text(encoding="utf-8", errors="replace")
        return Document(source=path.name, text=text, spans=line_spans(text))
    if suffix == ".pdf":
        return _load_pdf(path)
    raise ValueError(
        f"unsupported file type for {path.name!r}: expected one of "
        f"{', '.join(SUPPORTED_SUFFIXES)}"
    )


def _load_pdf(path: Path) -> Document:
    """Extract text page by page, joining pages with a blank line so the chunker
    sees a paragraph boundary between pages."""
    reader = PdfReader(str(path))
    page_texts = [(page.extract_text() or "") for page in reader.pages]

    parts: list[str] = []
    spans: list[Span] = []
    offset = 0
    for number, page_text in enumerate(page_texts, start=1):
        if not page_text.strip():
            continue  # blank page contributes no text and no span
        if number < len(page_texts):  # separate pages with a paragraph break
            if not page_text.endswith("\n"):
                page_text += "\n"
            if not page_text.endswith("\n\n"):
                page_text += "\n"
        parts.append(page_text)
        spans.append(Span(offset, offset + len(page_text), "page", number))
        offset += len(page_text)
    return Document(source=path.name, text="".join(parts), spans=tuple(spans))


def load_directory(
    path: str | Path, *, suffixes: tuple[str, ...] = SUPPORTED_SUFFIXES
) -> list[Document]:
    """Load every supported file directly inside `path`, sorted by filename.

    Hidden files (including .env-style dotfiles) are skipped; subdirectories are
    ignored on purpose — a docs folder in this repo is flat by convention.
    """
    root = Path(path)
    if not root.is_dir():
        raise FileNotFoundError(f"no such directory: {root}")
    documents = []
    for entry in sorted(root.iterdir()):
        if entry.is_file() and not entry.name.startswith(".") and entry.suffix.lower() in suffixes:
            document = load_file(entry)
            logger.debug("loaded %s (%d chars)", entry.name, len(document.text))
            documents.append(document)
    return documents

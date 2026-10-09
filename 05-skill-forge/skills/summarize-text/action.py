"""Extractive summarizer — the executable half of the summarize-text skill.

Classic frequency-scoring approach (a.k.a. TextRank without the graph):
sentences containing many rare-but-repeated content words score highest.
Pure stdlib, fully deterministic — same input, same summary, always.
"""

from __future__ import annotations

import re

STOPWORDS = frozenset(
    """a about above after again against all am an and any are as at be because
    been before being below between both but by could did do does doing down
    during each few for from further had has have having he her here hers herself
    him himself his how i if in into is it its itself just me more most my myself
    no nor not now of off on once only or other our ours ourselves out over own
    same she should so some such than that the their theirs them themselves then
    there these they this those through to too under until up very was we were
    what when where which while who whom why will with you your yours yourself
    yourselves""".split()
)

# Sentences are split on terminal punctuation followed by whitespace + a
# capital/digit. This keeps "e.g." and "3.14" intact in the common case.
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")


def split_sentences(text: str) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []
    parts = _SENTENCE.split(text)
    return [p.strip() for p in parts if p.strip()]


def _content_words(sentence: str) -> list[str]:
    words = re.findall(r"[a-z0-9']+", sentence.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 2]


def _stem(word: str) -> str:
    # Deliberately conservative: only the most common English suffixes.
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def summarize(text: str, *, max_ratio: float = 0.25, min_sentences: int = 1) -> dict:
    """Return dict with summary, keywords, and stats. See SKILL.md."""
    sentences = split_sentences(text)
    word_count = len(text.split())

    if len(sentences) < 3 or word_count < 40:
        return {
            "summary": text.strip(),
            "keywords": [],
            "original_words": word_count,
            "summary_words": word_count,
            "too_short": True,
        }

    # Frequency table over everything EXCEPT sentence 1 (often the title line).
    freq: dict[str, int] = {}
    for sentence in sentences[1:]:
        for word in _content_words(sentence):
            key = _stem(word)
            freq[key] = freq.get(key, 0) + 1

    scored: list[tuple[int, float]] = []
    for idx, sentence in enumerate(sentences):
        words = _content_words(sentence)
        if not words:
            scored.append((idx, 0.0))
            continue
        score = sum(freq.get(_stem(w), 0) for w in words) / len(words)
        scored.append((idx, score))

    keep = max(min_sentences, round(len(sentences) * 0.25)) if min_sentences else 0
    keep = min(keep, len(sentences))
    top = sorted(scored, key=lambda t: -t[1])[:keep]
    chosen = sorted(idx for idx, _ in top)  # restore original reading order
    summary = " ".join(sentences[i] for i in chosen)

    keywords = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    summary_words = len(summary.split())
    return {
        "summary": summary,
        "keywords": [k for k, _ in keywords],
        "original_words": word_count,
        "summary_words": summary_words,
        "too_short": False,
        "sentences_kept": keep,
        "sentences_total": len(sentences),
    }


def run(inputs: dict[str, str]) -> str:
    text = inputs.get("text", "").strip()
    if not text:
        raise ValueError("no text given — pass --input text=\"...\"")
    result = summarize(text)
    if result["too_short"]:
        return f"Too short to summarize ({result['original_words']} words) — returned as-is.\n\n{text}"
    pct = result["summary_words"] / max(1, result["original_words"]) * 100
    return "\n".join(
        [
            "SUMMARY",
            result["summary"],
            "",
            f"KEYWORDS   {', '.join(result['keywords'])}",
            f"STATS      {result['original_words']} words -> "
            f"{result['summary_words']} words ({pct:.0f}% of original), "
            f"{result['sentences_kept']}/{result['sentences_total']} sentences kept",
        ]
    )

"""Tools — the only way agents interact with the outside world.

A :class:`Tool` is a named, described callable. The description is what an
LLM reads to decide whether to call it, so descriptions read like
documentation, not implementation. Tools are executed by
:mod:`crew_engine.trace`-wrapped dispatch so every call lands in the audit
log — that log *is* the "what did the agents actually do?" answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

CORPUS_DIR = Path(__file__).resolve().parent.parent / "data" / "corpus"
ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "runs" / "artifacts"


@dataclass
class Tool:
    name: str
    description: str
    fn: Callable[..., str]

    def __call__(self, **kwargs) -> str:
        return self.fn(**kwargs)


@dataclass
class ToolRegistry:
    tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        if tool.name in self.tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self.tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self.tools[name]
        except KeyError:
            raise KeyError(f"no tool named {name!r}; have {sorted(self.tools)}") from None

    def descriptions(self) -> str:
        return "\n".join(f"- {t.name}: {t.description}" for t in self.tools.values())


# --------------------------------------------------------------------------
# Corpus helpers (shared by demo tools and tests)
# --------------------------------------------------------------------------

_STOP = frozenset(
    "a about after all also an and are as at be because been before between "
    "but by can could did do does each even every for from had has have he her "
    "his how i if in into is it its just like many may more most much my new no "
    "not now of off on one only or other our over say says she should so some "
    "such than that the their them then there these they this those three to "
    "two under up very was we were what when where which who why will with "
    "would you your".split()
)


def _sentences(text: str) -> list[str]:
    body = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", " ".join(body.split()))
    return [p.strip() for p in parts if p.strip()]


def load_corpus() -> dict[str, str]:
    """doc_name -> full text, from data/corpus/*.md (skip files named README)."""
    docs: dict[str, str] = {}
    for path in sorted(CORPUS_DIR.glob("*.md")):
        docs[path.stem] = path.read_text(encoding="utf-8")
    return docs


def corpus_search(query: str, k: int = 4) -> str:
    """Scan the bundled corpus for the sentences most relevant to ``query``.

    Relevance = fraction of query content words present in the sentence,
    with longer-matching sentences preferred. Returns formatted lines with
    ``[source]`` provenance so writers can cite honestly.
    """
    query_words = {w for w in re.findall(r"[a-z0-9]+", query.lower()) if w not in _STOP}
    if not query_words:
        return "corpus_search: query has no content words — nothing to match."

    hits: list[tuple[float, str, str]] = []
    for doc_name, text in load_corpus().items():
        for sentence in _sentences(text):
            words = {w for w in re.findall(r"[a-z0-9]+", sentence.lower()) if w not in _STOP}
            if not words:
                continue
            matched = len(query_words & words)
            if matched == 0:
                continue
            score = matched / len(query_words) + min(matched / len(words), 1.0) * 0.1
            hits.append((score, sentence, doc_name))

    hits.sort(key=lambda h: (-h[0], h[2]))
    if not hits:
        return "corpus_search: no matching sentences found."
    lines = [f"corpus_search({query!r}) top {k}:"]
    for score, sentence, doc in hits[:k]:
        lines.append(f"- ({score:.2f}) {sentence} [source: {doc}]")
    return "\n".join(lines)


def read_doc(name: str) -> str:
    """Return the full text of one corpus document."""
    path = CORPUS_DIR / f"{name.strip()}.md"
    if not path.exists():
        known = ", ".join(sorted(d.stem for d in CORPUS_DIR.glob("*.md")))
        return f"read_doc: unknown doc {name!r}. Known docs: {known}"
    text = path.read_text(encoding="utf-8")
    return f"--- {name} ---\n{text}"


def web_search(query: str) -> str:
    """Best-effort live search via DuckDuckGo Lite.

    Purely additive: every call is wrapped in try/except, and failure returns
    a labelled demo note rather than a traceback. Deterministic tests never
    hit this path.
    """
    try:
        import requests

        resp = requests.get(
            "https://lite.duckduckgo.com/lite/",
            params={"q": query},
            headers={"User-Agent": "crew-engine-demo/1.0"},
            timeout=6,
        )
        resp.raise_for_status()
        text = resp.text
        # Lite returns results in <a rel="nofollow" ...>Title</a> anchors.
        links = []
        for match in re.findall(r'<a rel="nofollow"[^>]*>(.*?)</a>', text)[:5]:
            title = re.sub(r"<[^>]+>", "", match).strip()
            if title:
                links.append(title)
        if links:
            return "web_search results:\n" + "\n".join(f"- {t}" for t in links)
    except Exception:
        pass
    return "web_search: offline or blocked — using demo corpus instead."


def now() -> str:
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d %H:%M")


def save_artifact(name: str, content: str) -> str:
    """Write an artifact under ARTIFACTS_DIR and report the path."""
    safe = re.sub(r"[^\w.-]+", "_", name.strip())
    out = ARTIFACTS_DIR / f"{safe}.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    return f"save_artifact: wrote {len(content)} chars to {out}"


def default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    for tool in (
        Tool("corpus_search",
             "Search a bundled offline corpus of articles. Each hit lists the "
             "sentence with a [source: <doc>] tag — use these as citations.",
             corpus_search),
        Tool("read_doc",
             "Read one full corpus document by name (e.g. read_doc(name='history-of-ai')).",
             read_doc),
        Tool("web_search",
             "Search the live web (best-effort; offline gracefully).",
             web_search),
        Tool("now", "Return the current date and time.", now),
        Tool("save_artifact",
             "Persist a named artifact to disk (name=..., content=...).",
             save_artifact),
    ):
        reg.register(tool)
    return reg
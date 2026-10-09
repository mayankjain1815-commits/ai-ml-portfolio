"""Blackboard — the shared memory where agents coordinate.

Instead of agents talking directly to each other (tight coupling), every
agent reads from and writes to one shared board (loose coupling). The board
keeps:

* **facts** — grounded statements with provenance (who found them, from
  which source). Writers must not invent facts; they assemble these.
* **messages** — the full audit log: who said what to whom, in order.
* **artifacts** — named deliverables (draft, report, plan).

This is the "post-it notes on the office whiteboard" model, and it is the
single most asked-about design decision in multi-agent interviews.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class Fact:
    content: str
    source: str          # doc name or web result label
    by_agent: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {"content": self.content, "source": self.source,
                "by_agent": self.by_agent}


@dataclass(frozen=True)
class Message:
    sender: str      # agent name or 'SYSTEM'
    text: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Blackboard:
    """Thread-safe-ish shared state (single-threaded by design; keep it so)."""

    def __init__(self) -> None:
        self.facts: list[Fact] = []
        self.messages: list[Message] = []
        self.artifacts: dict[str, str] = {}

    # -- facts -------------------------------------------------------------
    def add_fact(self, content: str, source: str, by_agent: str) -> None:
        fact = Fact(content=content, source=source, by_agent=by_agent)
        # Dedupe: the same sentence from the same source adds nothing.
        if not any(f.content == fact.content and f.source == fact.source for f in self.facts):
            self.facts.append(fact)

    def facts_for(self, topic: str) -> list[Fact]:
        """Facts relevant to ``topic`` — used to bound what a writer sees."""
        return [f for f in self.facts if _relevant(f.content, topic)]

    # -- messages ----------------------------------------------------------
    def say(self, sender: str, text: str) -> None:
        self.messages.append(Message(sender=sender, text=text))

    def transcript(self) -> str:
        return "\n".join(f"[{m.timestamp[:19]}] {m.sender}: {m.text}" for m in self.messages)

    # -- artifacts ---------------------------------------------------------
    def put_artifact(self, name: str, content: str) -> None:
        self.artifacts[name] = content

    def get_artifact(self, name: str) -> str | None:
        return self.artifacts.get(name)


def _relevant(text: str, topic: str) -> bool:
    topic_words = {w for w in topic.lower().split() if len(w) > 2}
    if not topic_words:
        return True
    lower = text.lower()
    return sum(1 for w in topic_words if w in lower) >= 1
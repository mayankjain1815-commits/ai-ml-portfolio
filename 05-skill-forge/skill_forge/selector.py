"""Skill selection — given a task in plain English, pick the right skill.

Two strategies behind one interface:

* :class:`KeywordSelector` — offline, deterministic, zero-cost. Scores each
  skill by trigger-word hits, name overlap and description-word overlap.
  It is genuinely useful (trigger lists are written to cover how people
  actually phrase things), which is why demo mode is a real implementation
  and not a placeholder.

* :class:`LLMSelector` — sends the candidate list (name + description only,
  never full skill bodies) to the model and asks for a single name back.
  Falls back to the keyword scorer if the model replies with something
  unknown. This mirrors how real agent frameworks do tool selection: the
  expensive context (skill bodies) is only loaded *after* the pick.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import llm
from .skill import Skill

_WORD = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset(
    "a an and are as at be by for from how i in is it of on or our so "
    "some that the this to use want with you your".split()
)


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in STOPWORDS and len(w) > 2}


@dataclass(frozen=True)
class Selection:
    """The winning skill plus enough context to explain the choice."""

    skill: Skill
    score: float
    alternatives: tuple[tuple[str, float], ...]  # (name, score), best-first
    strategy: str  # "keyword" or "llm"

    @property
    def confidence(self) -> str:
        """High / medium / low based on the margin over the runner-up."""
        if not self.alternatives:
            return "high"
        runner_up = self.alternatives[0][1]
        margin = self.score - runner_up
        if margin <= 0:
            return "low"
        if self.score > 0 and margin / self.score >= 0.4:
            return "high"
        return "medium"


class KeywordSelector:
    """Deterministic scorer. +3 per trigger hit, +2 per name-word hit,
    +1 per description-word hit — small integer weights keep it debuggable
    by hand, which matters when someone asks 'why did it pick that?'."""

    TRIGGER_WEIGHT = 3.0
    NAME_WEIGHT = 2.0
    DESC_WEIGHT = 1.0

    def __init__(self, skills: list[Skill]):
        self.skills = list(skills)

    def score(self, task: str, skill: Skill) -> float:
        task_words = _words(task)
        task_lower = task.lower()

        score = 0.0
        for trigger in skill.triggers:
            if re.search(rf"\b{re.escape(trigger.lower())}\b", task_lower):
                score += self.TRIGGER_WEIGHT

        score += self.NAME_WEIGHT * len(_words(skill.name) & task_words)
        score += self.DESC_WEIGHT * len(_words(skill.description) & task_words)
        return score

    def select(self, task: str) -> Selection:
        scored = sorted(
            ((s, self.score(task, s)) for s in self.skills),
            key=lambda pair: (-pair[1], pair[0].name),
        )
        best, best_score = scored[0]
        alts = tuple((s.name, sc) for s, sc in scored[1:4] if sc > 0)
        # A task that matches nothing should not silently get a random skill.
        if best_score == 0:
            best = _fallback_skill(self.skills)
        return Selection(best, best_score, alts, strategy="keyword")


def _fallback_skill(skills: list[Skill]) -> Skill:
    """When nothing matches, prefer the generic helper skill if present."""
    for name in ("debug-helper", "summarize-text"):
        for s in skills:
            if s.name == name:
                return s
    return skills[0]


class LLMSelector:
    """Ask the model to choose exactly one skill name from a candidate list."""

    SYSTEM = (
        "You are a skill router. You pick exactly one skill from a list, "
        "or the word NONE if no skill applies. Reply with the skill name "
        "alone — no punctuation, no explanation."
    )

    def __init__(self, skills: list[Skill], fallback: KeywordSelector | None = None):
        self.skills = list(skills)
        self.fallback = fallback or KeywordSelector(self.skills)

    def select(self, task: str) -> Selection:
        if not llm.have_key():
            selection = self.fallback.select(task)
            return Selection(
                selection.skill,
                selection.score,
                selection.alternatives,
                strategy="keyword (no API key)",
            )

        roster = "\n".join(f"- {s.name}: {s.description}" for s in self.skills)
        prompt = f"Skills:\n{roster}\n\nTask: {task}\n\nSkill name:"
        try:
            reply = llm.complete(prompt, system=self.SYSTEM).strip().strip(".,\"'")
        except Exception:
            selection = self.fallback.select(task)
            return Selection(
                selection.skill, selection.score, selection.alternatives,
                strategy="keyword (model unavailable)",
            )

        for skill in self.skills:
            if skill.name.lower() == reply.lower():
                keyword = self.fallback.select(task)
                return Selection(
                    skill,
                    score=keyword.score if skill.name == keyword.skill.name else 10.0,
                    alternatives=keyword.alternatives,
                    strategy="llm",
                )
        # Model replied with something unknown — fall back rather than crash.
        selection = self.fallback.select(task)
        return Selection(
            selection.skill, selection.score, selection.alternatives,
            strategy="keyword (invalid model reply)",
        )

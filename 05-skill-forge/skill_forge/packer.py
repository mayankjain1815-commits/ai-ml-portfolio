"""Prompt packing — load one skill into a bounded system prompt.

The core idea this project teaches: **skills are context-window management.**
A model with 9 loaded skills in its system prompt pays for all nine on every
single request. A model that loads only the chosen skill pays for one.
This module makes that trade-off explicit and measurable.

:func:`pack` assembles ``[role] + [skill body] + [task]`` and guarantees the
result fits a token budget (estimated at ~4 chars/token, the usual English
rough cut). If the skill body overflows, we trim *whole lines* from its end
— never mid-line — and report exactly how much was dropped so the caller can
see the cost of a too-big skill.
"""

from __future__ import annotations

from dataclasses import dataclass

from .skill import Skill

DEFAULT_BUDGET = 1200  # tokens — small on purpose: this is a teaching tool
HARD_FLOOR = 200  # below this the header alone may not fit; we refuse


def estimate_tokens(text: str) -> int:
    """~4 characters per token. Crude, but consistent — and consistency is
    what a budget needs; a tokenizer would only make the estimate prettier."""
    return max(1, len(text) // 4) if text else 0


@dataclass(frozen=True)
class PackedPrompt:
    text: str
    tokens: int
    budget: int
    truncated_lines: int  # how many skill-body lines were dropped (0 = none)

    @property
    def fitted(self) -> bool:
        return self.truncated_lines == 0

    @property
    def utilisation(self) -> float:
        return self.tokens / self.budget if self.budget else 0.0


HEADER = (
    "You are an AI assistant. Follow the skill instructions below exactly "
    "when handling the user's task. Cite which skill step you used."
)

FOOTER = "Task: {task}\n\nRespond with the result only."


def pack(
    skill: Skill,
    task: str,
    *,
    budget: int = DEFAULT_BUDGET,
    history: str | None = None,
) -> PackedPrompt:
    """Build a system+user prompt pair that fits inside ``budget`` tokens.

    ``history`` (optional) is an already-summarised conversation snippet —
    packed *before* the skill body, because remembering who you are talking
    to beats remembering step 7 of a checklist.
    """
    if budget < HARD_FLOOR:
        raise ValueError(f"budget must be at least {HARD_FLOOR} tokens")

    prelude = HEADER
    if history:
        prelude += f"\n\nConversation so far:\n{history}"

    footer = FOOTER.format(task=task)
    # Body starts whole; we trim only if we must. The 'dropped' notice is
    # part of the measured text so the fit guarantee is exact, not approximate.
    body_lines = skill.body.splitlines()
    dropped = 0

    def assemble(body: str, dropped: int) -> str:
        text = f"{prelude}\n\n--- SKILL: {skill.name} ---\n{body}\n---\n\n{footer}"
        if dropped:
            text += f"\n[skill body truncated: {dropped} lines dropped to fit budget]"
        return text

    text = assemble(skill.body, 0)
    while estimate_tokens(text) > budget and body_lines:
        body_lines.pop()
        dropped += 1
        text = assemble("\n".join(body_lines), dropped)

    if estimate_tokens(text) > budget:
        raise ValueError(
            f"Task + header alone exceed the {budget}-token budget. "
            "Shorten the task or raise --budget."
        )

    return PackedPrompt(
        text=text,
        tokens=estimate_tokens(text),
        budget=budget,
        truncated_lines=dropped,
    )

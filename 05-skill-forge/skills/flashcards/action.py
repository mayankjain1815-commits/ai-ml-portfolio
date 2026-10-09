"""Flashcard deck builder — the executable half of the flashcards skill.

Deterministic "shuffle": seeded by the deck content itself, so the same
deck always produces the same test order without the user picking a seed.
"""

from __future__ import annotations

import random
import re

MAX_ANSWER_WORDS = 20


def parse_cards(raw: str) -> tuple[list[tuple[str, str]], list[str]]:
    """Split ``Q :: A;; Q2 :: A2`` into cards + a list of malformed entries."""
    cards: list[tuple[str, str]] = []
    errors: list[str] = []
    for i, chunk in enumerate(raw.split(";;"), start=1):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "::" not in chunk:
            errors.append(f"card {i}: missing '::' between question and answer")
            continue
        question, _, answer = chunk.partition("::")
        question, answer = question.strip(), answer.strip()
        if not question or not answer:
            errors.append(f"card {i}: empty question or answer")
            continue
        cards.append((question, answer))
    return cards, errors


def run(inputs: dict[str, str]) -> str:
    raw = inputs.get("cards", "").strip()
    if not raw:
        raise ValueError(
            'no cards given — e.g. --input cards="What is RAM? :: Working memory;;'
            'What is a CPU? :: The brain"'
        )

    cards, errors = parse_cards(raw)
    if not cards:
        raise ValueError("no valid cards. Format: Q :: A;; Q :: A")

    lines = [f"DECK  {len(cards)} cards"]
    for i, (question, answer) in enumerate(cards, start=1):
        lines.append(f"{i}. Q: {question}")
        lines.append(f"   A: {answer}")

    if errors:
        lines.append("SKIPPED")
        lines.extend(f"   - {e}" for e in errors)

    # Stable shuffle seeded by deck content.
    seed = sum(ord(c) for c in raw) % (2**32)
    order = list(range(1, len(cards) + 1))
    random.Random(seed).shuffle(order)
    lines.append(f"SELF-TEST ORDER  {', '.join(map(str, order))}")

    q_words = [len(re.findall(r"\w+", q)) for q, _ in cards]
    long_answers = [i for i, (_, a) in enumerate(cards, 1)
                    if len(re.findall(r"\w+", a)) > MAX_ANSWER_WORDS]
    notes = [f"avg question {sum(q_words) / len(q_words):.0f} words"]
    if long_answers:
        notes.append(
            f"card(s) {', '.join(map(str, long_answers))} exceed "
            f"{MAX_ANSWER_WORDS} words — split them, long answers kill recall"
        )
    seen: dict[str, int] = {}
    for question, _ in cards:
        key = question.lower()
        seen[key] = seen.get(key, 0) + 1
    dupes = [q for q, n in seen.items() if n > 1]
    if dupes:
        notes.append(f"duplicate question(s): {', '.join(dupes)}")
    lines.append(f"STATS            {' | '.join(notes)}")
    return "\n".join(lines)

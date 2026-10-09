"""Weekly study-schedule builder — the executable half of the study-plan skill.

Deterministic by design: given the same inputs, the same student gets the
same plan, so it can be tested and argued about.
"""

from __future__ import annotations

DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
BLOCK_MINUTES = 30
MAX_DAILY_HOURS = 4.0


def parse_subjects(raw: str) -> dict[str, float]:
    """``"math=3, history"`` -> ``{"math": 3.0, "history": 1.0}``."""
    subjects: dict[str, float] = {}
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        name, sep, weight = chunk.partition("=")
        if sep:
            try:
                w = float(weight)
            except ValueError as exc:
                raise ValueError(f"weight for {name.strip()!r} must be a number") from exc
        else:
            w = 1.0
        if w < 0:
            raise ValueError(f"weight for {name.strip()!r} cannot be negative")
        subjects[name.strip()] = subjects.get(name.strip(), 0.0) + w
    if not subjects:
        raise ValueError("no subjects given — e.g. --input subjects='math,history'")
    return subjects


def allocate(subjects: dict[str, float], hours: float) -> tuple[dict[str, float], list[str]]:
    """Weekly hours per subject (30-min blocks), plus any zero-weight drops."""
    blocks_total = int(round(hours * 60 / BLOCK_MINUTES))
    weights = {s: w for s, w in subjects.items() if w > 0}
    dropped = [s for s, w in subjects.items() if w == 0]
    if not weights:
        raise ValueError("all subject weights are zero — nothing to plan")

    weight_sum = sum(weights.values())
    raw = {s: blocks_total * w / weight_sum for s, w in weights.items()}
    blocks = {s: int(v) for s, v in raw.items()}
    # Give leftover blocks to the largest fractional remainders (fair rounding).
    leftover = blocks_total - sum(blocks.values())
    remainder_order = sorted(raw, key=lambda s: raw[s] - blocks[s], reverse=True)
    for i in range(leftover):
        blocks[remainder_order[i % len(remainder_order)]] += 1
    return {s: b * BLOCK_MINUTES / 60 for s, b in blocks.items() if b > 0}, dropped


def build_schedule(hours_per_subject: dict[str, float], days: int) -> list[list[str]]:
    """Spread each subject across the week; heavier subjects start earlier."""
    day_count = min(max(days, 1), 7)
    day_hours = [0.0] * day_count
    grid: list[list[str]] = [[] for _ in range(day_count)]

    ordered = sorted(hours_per_subject.items(), key=lambda kv: -kv[1])
    for subject, hours in ordered:
        blocks = int(round(hours * 60 / BLOCK_MINUTES))
        # Prefer days with the least load; tie-break to earlier in the week.
        order = sorted(range(day_count), key=lambda d: (day_hours[d], d))
        for i in range(blocks):
            d = order[i % day_count]
            slot = len(grid[d])
            start_h = 18 + (slot // 2)          # evening study blocks
            start_m = 0 if slot % 2 == 0 else 30
            end_h, end_m = (start_h, start_m + 30)
            if end_m == 60:
                end_h, end_m = start_h + 1, 0
            grid[d].append(
                f"{start_h:02d}:{start_m:02d}-{end_h:02d}:{end_m:02d} {subject}"
            )
            day_hours[d] += 0.5
    return grid


def run(inputs: dict[str, str]) -> str:
    subjects = parse_subjects(inputs.get("subjects", ""))
    try:
        hours = float(inputs.get("hours", "5"))
        days = int(float(inputs.get("days", "5")))
    except ValueError as exc:
        raise ValueError("hours and days must be numbers") from exc
    if hours <= 0:
        return "Nothing to plan: hours must be positive (got 0 or less)."
    if days <= 0:
        days = 5

    allocated, dropped = allocate(subjects, hours)
    grid = build_schedule(allocated, days)

    lines = [f"WEEKLY STUDY PLAN — {hours:g}h over {min(days, 7)} days"]
    for i, slots in enumerate(grid):
        body = "   ".join(slots) if slots else "rest / catch-up"
        lines.append(f"{DAYS[i]:<4} {body}")

    totals = " | ".join(f"{s} {h:g}h" for s, h in
                        sorted(allocated.items(), key=lambda kv: -kv[1]))
    lines.append(f"TOTALS   {totals}")

    notes: list[str] = []
    for subject, h in allocated.items():
        if h < 1:
            notes.append(f"{subject} gets only {h:g}h/week — below the 1h minimum to stick")
    if dropped:
        notes.append(f"excluded (weight 0): {', '.join(dropped)}")
    if days < 7:
        notes.append("one rest day kept free on purpose — recovery is part of the plan")
    for i, slots in enumerate(grid):
        day_h = len(slots) * 0.5
        if day_h > MAX_DAILY_HOURS:
            notes.append(f"{DAYS[i]} hits {day_h:g}h — over the {MAX_DAILY_HOURS:g}h sustainability cap")
    if not notes:
        notes.append("load is balanced — same time each day, nothing over 4h")
    lines.append("NOTES    " + f"\n         ".join(f"- {n}" for n in notes))
    return "\n".join(lines)

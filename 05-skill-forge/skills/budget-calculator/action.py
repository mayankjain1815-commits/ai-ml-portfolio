"""Monthly budget breakdown vs the 50/30/20 rule — budget-calculator's action.

Money is handled in integer cents internally so `$0.1 + $0.2` never becomes
`$0.30000000000000004` — the classic float-money bug, avoided by design.
"""

from __future__ import annotations

RULE = {"needs": 50.0, "wants": 30.0, "savings": 20.0}


def classify(category: str) -> str:
    low = category.strip().lower()
    if low.startswith("need"):
        return "needs"
    if low.startswith("save") or low.startswith("saving"):
        return "savings"
    return "wants"  # default bucket: unknown categories are discretionary


def _money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}${cents // 100:,}.{cents % 100:02d}"


def _to_cents(raw: str) -> int:
    return int(round(float(raw.replace(",", "").replace("$", "")) * 100))


def run(inputs: dict[str, str]) -> str:
    if "income" not in inputs:
        raise ValueError("income is required — e.g. --input income=3000")
    income = _to_cents(inputs["income"])
    if income < 0:
        raise ValueError("income cannot be negative")

    expenses: list[tuple[str, int, str]] = []
    for key, value in inputs.items():
        if key == "income":
            continue
        expenses.append((key, _to_cents(value), classify(key)))
    expenses.sort(key=lambda e: -e[1])

    spent = sum(amount for _, amount, _ in expenses)
    leftover = income - spent

    buckets = {"needs": 0, "wants": 0, "savings": 0}
    for _, amount, bucket in expenses:
        buckets[bucket] += amount
    buckets["savings"] += max(leftover, 0)  # unspent money counts as savings

    lines = [f"INCOME     {_money(income)} / month", "SPENDING"]
    if not expenses:
        lines.append("  (no expense categories given)")
    for name, amount, bucket in expenses:
        pct = amount / income * 100 if income else 0.0
        lines.append(f"  {name:<10} {_money(amount):>10}   {pct:5.1f}%   {bucket}")

    actual = {b: (c / income * 100 if income else 0.0) for b, c in buckets.items()}
    totals = " | ".join(f"{b} {actual[b]:.1f}%" for b in ("needs", "wants", "savings"))
    lines.append(f"TOTALS     {totals} | leftover {_money(leftover)}")

    lines.append("50/30/20")
    for bucket, target_pct in RULE.items():
        target = int(income * target_pct / 100)
        gap = buckets[bucket] - target
        lines.append(
            f"           {bucket:<8} {_money(buckets[bucket])} vs "
            f"{_money(target)} target ({target_pct:.0f}%) "
            f"({'+' if gap >= 0 else '-'}{_money(abs(gap))})"
        )

    if leftover < 0:
        biggest = expenses[0][0] if expenses else "?"
        verdict = (
            f"OVERSPENDING by {_money(abs(leftover))} — "
            f"'{biggest}' is the biggest line item; cut there first."
        )
    elif actual["savings"] < 10:
        verdict = (
            f"Savings are {actual['savings']:.1f}% of income — below the 10% "
            "floor. Fine short-term, dangerous for more than a few months."
        )
    else:
        off = [
            b for b in RULE
            if abs(actual[b] - RULE[b]) > 5.0
        ]
        verdict = (
            "On track — every bucket within 5 points of the 50/30/20 target."
            if not off
            else f"Workable, but {', '.join(off)} drift more than 5 points from target."
        )
    lines.append(f"VERDICT    {verdict}")
    return "\n".join(lines)

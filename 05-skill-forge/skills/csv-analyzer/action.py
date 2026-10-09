"""Deterministic CSV profiling — the executable half of the csv-analyzer skill.

Stdlib only (`csv` + `statistics`): the point of an *action* skill is that it
runs anywhere, including offline CI, with zero installs.
"""

from __future__ import annotations

import csv
import statistics
from pathlib import Path

MISSING_TOKENS = {"", "na", "n/a", "nan", "null", "none", "-", "?"}


def _is_missing(value: str) -> bool:
    return value.strip().lower() in MISSING_TOKENS


def _as_float(value: str) -> float | None:
    try:
        return float(value.replace(",", "").strip())
    except (ValueError, AttributeError):
        return None


def _profile_column(name: str, values: list[str]) -> dict:
    total = len(values)
    missing = sum(1 for v in values if _is_missing(v))
    present = [v for v in values if not _is_missing(v)]
    numerics = [(v, n) for v in present if (n := _as_float(v)) is not None]
    numeric_ratio = len(numerics) / len(present) if present else 0.0

    col = {
        "name": name,
        "type": "numeric" if present and numeric_ratio >= 0.8 else "categorical",
        "missing": missing,
        "missing_pct": (missing / total * 100) if total else 0.0,
    }

    if col["type"] == "numeric":
        nums = [n for _, n in numerics]
        col.update(
            min=min(nums), max=max(nums),
            mean=statistics.fmean(nums),
            median=statistics.median(nums),
            std=statistics.pstdev(nums) if len(nums) > 1 else 0.0,
        )
    else:
        counts: dict[str, int] = {}
        for v in present:
            counts[v] = counts.get(v, 0) + 1
        col["top"] = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
        col["distinct"] = len(counts)
    return col


def _warnings(profiles: list[dict], header: list[str]) -> list[str]:
    warnings: list[str] = []
    for col in profiles:
        low = col["name"].lower()
        if col["missing_pct"] > 20:
            warnings.append(f"{col['name']}: {col['missing_pct']:.1f}% values missing")
        if col["type"] == "numeric":
            if "age" in low or "price" in low or "amount" in low:
                if col["min"] < 0:
                    warnings.append(f"{col['name']}: contains negatives (min={col['min']:g})")
            if col["median"] and abs(col["max"]) > 10 * abs(col["median"]):
                warnings.append(
                    f"{col['name']}: max={col['max']:g} vs median={col['median']:g} "
                    "— likely a typo or unit error"
                )
            if col["std"] == 0:
                warnings.append(f"{col['name']}: constant column, no information")
        elif col["distinct"] == 1:
            warnings.append(f"{col['name']}: only one distinct value")
    if len(header) != len(set(header)):
        warnings.append("duplicate column names in header")
    return warnings


def run(inputs: dict[str, str]) -> str:
    path = Path(inputs.get("path", "")).expanduser()
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — pass the file with --input path=file.csv"
        )

    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    if not rows:
        raise ValueError("file is empty")

    header = rows[0]
    has_header = any(c.strip() for c in header)
    data = rows[1:] if has_header else rows
    if not has_header:
        header = [f"col_{i + 1}" for i in range(len(rows[0]))]

    # Ragged rows (wrong number of fields) are the #1 real-world CSV problem.
    ragged = sum(1 for r in data if len(r) != len(header))
    width = max((len(r) for r in rows), default=0)

    columns: list[dict] = []
    for i, name in enumerate(header):
        values = [(r[i] if i < len(r) else "") for r in data]
        columns.append(_profile_column(name.strip() or f"col_{i + 1}", values))

    lines: list[str] = []
    lines.append(f"SHAPE       {len(data)} rows × {len(header)} columns"
                 + ("" if has_header else "  (no header row — assumed)"))
    if ragged:
        lines.append(f"WARNING     {ragged} ragged row(s); widest row has {width} fields")
    lines.append("COLUMNS")
    for col in columns:
        lines.append(f"            {col['name']} ({col['type']}) "
                     f"— {col['missing_pct']:.1f}% missing")
    lines.append("STATS")
    for col in columns:
        if col["type"] == "numeric":
            lines.append(
                f"            {col['name']}: min={col['min']:g} max={col['max']:g} "
                f"mean={col['mean']:.2f} median={col['median']:g} std={col['std']:.2f}"
            )
    lines.append("TOP VALUES")
    for col in columns:
        if col["type"] == "categorical":
            top = ", ".join(f"{v} ({n})" for v, n in col["top"])
            lines.append(f"            {col['name']}: {top} — {col['distinct']} distinct")

    warnings = _warnings(columns, header)
    if warnings:
        lines.append("WARNINGS")
        lines.extend(f"            - {w}" for w in warnings)
    else:
        lines.append("WARNINGS    none found")

    missing_total = sum(c["missing"] for c in columns)
    verdict = (
        f"Clean enough to use — {len(columns)} columns, {missing_total} missing cells, "
        f"{len(warnings)} issue(s) to review."
        if warnings else
        f"Clean — {len(columns)} columns, no issues detected."
    )
    lines.append(f"VERDICT     {verdict}")
    return "\n".join(lines)

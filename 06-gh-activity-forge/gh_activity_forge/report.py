"""Write the four (or five) output artifacts for one activity plan.

Outputs, all into ``--output``:

- ``contribution.svg``  — the hand-built GitHub-style graph.
- ``activity.json``     — full structured data: range, profile, seed, totals,
  and one entry per day (the machine-readable source of truth).
- ``summary.md``        — human-readable summary: totals, busiest day,
  longest streak, per-month table.
- ``report.html``       — dark GitHub-like page with the SVG embedded inline;
  fully offline (no CDN, no external fonts, no scripts).
- ``fake_commits.sh``   — only when the user explicitly asked to emit it.
"""

from __future__ import annotations

import json
from pathlib import Path

from .git_script import write_git_script
from .generator import DayActivity, longest_streak, total_commits
from .svg import render_svg

#: Basename of every file, in the order :func:`write_outputs` produces them.
OUTPUT_FILES: tuple[str, ...] = (
    "contribution.svg",
    "activity.json",
    "summary.md",
    "report.html",
)
GIT_SCRIPT_NAME = "fake_commits.sh"


def busiest_day(activities: list[DayActivity]) -> DayActivity:
    """The day with the most commits; earliest wins on ties."""
    return max(activities, key=lambda a: a.commit_count)


def month_totals(activities: list[DayActivity]) -> list[tuple[str, int, int]]:
    """Per-month (key, commits, active_days) in ascending order.

    Key is ``YYYY-MM`` so months sort correctly and stay unambiguous even
    for ranges that span multiple years.
    """
    buckets: dict[str, list[int]] = {}
    for activity in activities:
        key = f"{activity.date.year:04d}-{activity.date.month:02d}"
        entry = buckets.setdefault(key, [0, 0])
        entry[0] += activity.commit_count
        if activity.commit_count > 0:
            entry[1] += 1
    return [(key, commits, active) for key, (commits, active) in buckets.items()]


def _stats(activities: list[DayActivity]) -> dict[str, object]:
    """Shared totals used by the JSON, the Markdown summary and the HTML."""
    busiest = busiest_day(activities)
    return {
        "commits": total_commits(activities),
        "days": len(activities),
        "active_days": sum(1 for a in activities if a.commit_count > 0),
        "zero_days": sum(1 for a in activities if a.commit_count == 0),
        "busiest_day": {
            "date": busiest.date.isoformat(),
            "commits": busiest.commit_count,
        },
        "longest_streak_days": longest_streak(activities),
    }


def render_json(
    activities: list[DayActivity], *, profile: str, seed: int
) -> str:
    """The full structured plan as pretty-printed JSON."""
    stats = _stats(activities)
    payload = {
        "generator": "gh-activity-forge",
        "profile": profile,
        "seed": seed,
        "range": {
            "start": activities[0].date.isoformat(),
            "end": activities[-1].date.isoformat(),
            "days": len(activities),
        },
        "totals": stats,
        "per_day": [
            {"date": a.date.isoformat(), "commits": a.commit_count}
            for a in activities
        ],
    }
    return json.dumps(payload, indent=2) + "\n"


def render_summary(
    activities: list[DayActivity], *, profile: str, seed: int
) -> str:
    """Human-readable Markdown summary of the plan."""
    stats = _stats(activities)
    start, end = activities[0].date, activities[-1].date
    active_pct = 100.0 * stats["active_days"] / stats["days"]  # type: ignore[operator]

    lines = [
        f"# Contribution plan — {start.isoformat()} to {end.isoformat()}",
        "",
        f"- **Profile:** {profile} (seed {seed})",
        (
            f"- **Total commits:** {stats['commits']:,} over {stats['days']} days"
        ),
        (
            f"- **Active days:** {stats['active_days']} "
            f"({active_pct:.1f}%) — {stats['zero_days']} zero-commit days"
        ),
        (
            f"- **Busiest day:** {stats['busiest_day']['date']} "  # type: ignore[index]
            f"with {stats['busiest_day']['commits']} commits"  # type: ignore[index]
        ),
        f"- **Longest streak:** {stats['longest_streak_days']} consecutive days",
        "",
        "## Month by month",
        "",
        "| Month | Commits | Active days |",
        "| --- | ---: | ---: |",
    ]
    for key, commits, active in month_totals(activities):
        lines.append(f"| {key} | {commits} | {active} |")
    lines.append("")
    lines.append(
        "_Generated offline by gh-activity-forge — demo data, "
        "not a record of real work._"
    )
    return "\n".join(lines) + "\n"


def render_html(
    svg_text: str, activities: list[DayActivity], *, profile: str, seed: int
) -> str:
    """A dark, GitHub-like single-page report with the SVG inline.

    Everything (styles included) lives in this one file — opening it works
    with networking turned off.
    """
    stats = _stats(activities)
    start, end = activities[0].date, activities[-1].date
    # The XML declaration is only valid at the start of a document; drop it
    # when embedding the SVG inside HTML.
    svg_inline = svg_text.strip()
    if svg_inline.startswith("<?xml"):
        svg_inline = svg_inline.split("?>", 1)[1].strip()

    period = (
        str(start.year)
        if start.year == end.year
        else f"{start.year}-{end.year}"
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Contribution report — {period}</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: #0d1117;
    color: #e6edf3;
    font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
  }}
  header {{
    padding: 20px 28px;
    border-bottom: 1px solid #30363d;
  }}
  h1 {{ margin: 0; font-size: 18px; font-weight: 600; }}
  .sub {{ margin-top: 6px; color: #7d8590; font-size: 13px; }}
  .stats {{ margin-top: 12px; display: flex; gap: 20px; flex-wrap: wrap; }}
  .stat {{ font-size: 13px; }}
  .stat b {{ font-size: 16px; display: block; }}
  main {{ padding: 24px 28px; max-width: 980px; }}
  .card {{
    background: #ffffff;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 14px;
    overflow-x: auto;
  }}
  footer {{
    padding: 8px 28px 28px;
    color: #7d8590;
    font-size: 12px;
  }}
</style>
</head>
<body>
<header>
  <h1>Contribution report — {period}</h1>
  <div class="sub">{start.isoformat()} to {end.isoformat()} ·
profile {profile} · seed {seed}</div>
  <div class="stats">
    <span class="stat"><b>{stats["commits"]:,}</b> commits</span>
    <span class="stat"><b>{stats["active_days"]}</b> active days</span>
    <span class="stat"><b>{stats["longest_streak_days"]}</b>-day streak</span>
    <span class="stat"><b>{stats["busiest_day"]["commits"]}</b> on
{stats["busiest_day"]["date"]}</span>
  </div>
</header>
<main>
  <div class="card">
{svg_inline}
  </div>
</main>
<footer>
  Generated offline by gh-activity-forge. Demo data — green squares are not
real engineering.
</footer>
</body>
</html>
"""


def write_outputs(
    out_dir: Path,
    activities: list[DayActivity],
    *,
    profile: str,
    seed: int,
    emit_git_script: bool = False,
) -> list[Path]:
    """Write every requested artifact into ``out_dir``; return the paths.

    Creates ``out_dir`` if needed. ``fake_commits.sh`` is only written when
    ``emit_git_script`` is True — generating it is always an explicit,
    opt-in decision by the user.
    """
    if not activities:
        raise ValueError("cannot write outputs for an empty activity list")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    svg_text = render_svg(activities)
    written: list[Path] = []

    for name, content in (
        ("contribution.svg", svg_text),
        ("activity.json", render_json(activities, profile=profile, seed=seed)),
        ("summary.md", render_summary(activities, profile=profile, seed=seed)),
        (
            "report.html",
            render_html(svg_text, activities, profile=profile, seed=seed),
        ),
    ):
        path = out_dir / name
        path.write_text(content, encoding="utf-8")
        written.append(path)

    if emit_git_script:
        written.append(
            write_git_script(
                out_dir / GIT_SCRIPT_NAME, activities, profile=profile, seed=seed
            )
        )
    else:
        _remove_stale_git_script(out_dir / GIT_SCRIPT_NAME)
    return written


def _remove_stale_git_script(path: Path) -> None:
    """Drop a previously generated ``fake_commits.sh`` when not re-emitting.

    Without this, regenerating the safe outputs into the same directory would
    leave a backdated-commit script that no longer matches the plan. Only a
    file that carries our own generated header is ever removed — anything
    else is left untouched.
    """
    if not path.exists():
        return
    head = path.read_text(encoding="utf-8", errors="ignore")[:300]
    if "generated by gh-activity-forge" in head:
        path.unlink()

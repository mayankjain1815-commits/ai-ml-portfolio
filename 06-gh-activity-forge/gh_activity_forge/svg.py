"""Hand-built GitHub-style contribution graph, rendered as SVG by hand.

Rendering decisions (documented here because the tests pin them down):

- Rows are **Sunday..Saturday**, exactly like GitHub. ``datetime.date`` gives
  Monday=0..Sunday=6, so row index = ``(weekday + 1) % 7``.
- Columns are weeks starting Sunday. Column index = days since the Sunday on
  or before the range's first day, so the first day lands in its correct
  weekday row and a full year spans 53 columns x 7 rows.
- Only days inside the range get a cell; the padding days of the first and
  last columns are simply absent. A full-year range therefore yields exactly
  365 (or 366) cells.
- GitHub's exact five-level light palette, with these bucket edges:
  ``0 -> level 0``, ``1-2 -> level 1``, ``3-5 -> level 2``,
  ``6-9 -> level 3``, ``10+ -> level 4``.
- Cell size 11 px with a 3 px gap (14 px pitch), rounded corners (rx=2).
"""

from __future__ import annotations

from datetime import date, timedelta
from xml.sax.saxutils import escape

from .generator import DayActivity

#: Geometry shared with the tests: 11 px cells, 3 px gaps, 14 px pitch.
CELL = 11
GAP = 3
PITCH = CELL + GAP

#: Left margin for weekday labels, top margin above the grid.
GRID_LEFT = 32
GRID_TOP = 42

#: GitHub's five contribution levels, light theme (index == level).
LEVEL_COLORS: tuple[str, ...] = (
    "#ebedf0",  # level 0 — empty
    "#9be9a8",  # level 1
    "#40c463",  # level 2
    "#30a14e",  # level 3
    "#216e39",  # level 4
)

_TEXT = "#24292f"
_MUTED = "#57606a"

_WEEKDAY_LABELS: dict[int, str] = {1: "Mon", 3: "Wed", 5: "Fri"}


def level_for(count: int) -> int:
    """Map a commit count to its 0-4 bucket.

    Edges: 0 -> 0, 1-2 -> 1, 3-5 -> 2, 6-9 -> 3, 10+ -> 4.
    """
    if count <= 0:
        return 0
    if count < 3:
        return 1
    if count < 6:
        return 2
    if count < 10:
        return 3
    return 4


def _first_sunday_on_or_before(day: date) -> date:
    """Start of the week column containing ``day`` (Sunday-first rows)."""
    return day - timedelta(days=(day.weekday() + 1) % 7)


def _column(day: date, first_sunday: date) -> int:
    """Zero-based week column of ``day``."""
    return (day - first_sunday).days // 7


def _row(day: date) -> int:
    """Zero-based row of ``day`` (0 = Sunday ... 6 = Saturday)."""
    return (day.weekday() + 1) % 7


def _tooltip(count: int, day: date) -> str:
    """GitHub-style tooltip: '14 contributions on Tuesday, March 3, 2026'."""
    noun = "contribution" if count == 1 else "contributions"
    return f"{count} {noun} on {day.strftime('%A, %B')} {day.day}, {day.year}"


def _caption(activities: list[DayActivity]) -> str:
    """Caption above the graph, mirroring GitHub's wording."""
    total = sum(a.commit_count for a in activities)
    start, end = activities[0].date, activities[-1].date
    full_years = (
        start.month == 1
        and start.day == 1
        and end.month == 12
        and end.day == 31
    )
    if full_years and start.year == end.year:
        return f"{total:,} contributions in {start.year}"
    if full_years:
        return f"{total:,} contributions in {start.year}-{end.year}"
    return (
        f"{total:,} contributions from {start.isoformat()} to {end.isoformat()}"
    )


def _month_labels(
    activities: list[DayActivity], first_sunday: date
) -> list[tuple[int, str]]:
    """(column, label) for the first in-range day of each month.

    Labels closer than 3 columns to the previously *shown* one are dropped
    so text never overlaps on short or odd ranges.
    """
    labels: list[tuple[int, str]] = []
    previous_month: tuple[int, int] | None = None
    previous_col = -99
    for activity in activities:
        month_key = (activity.date.year, activity.date.month)
        if month_key == previous_month:
            continue
        previous_month = month_key
        col = _column(activity.date, first_sunday)
        if col - previous_col < 3:
            continue  # would visually collide with the previous label
        previous_col = col
        labels.append((col, activity.date.strftime("%b")))
    return labels


def render_svg(activities: list[DayActivity], *, title: str | None = None) -> str:
    """Render the plan as a standalone SVG document (valid XML).

    Args:
        activities: one DayActivity per day, ascending; all days must be
            contiguous (the generator guarantees this).
        title: overrides the default caption text; it is XML-escaped, so
            odd characters like ``&`` cannot break the document.

    Raises:
        ValueError: if ``activities`` is empty.
    """
    if not activities:
        raise ValueError("cannot render an SVG from an empty activity list")

    start, end = activities[0].date, activities[-1].date
    first_sunday = _first_sunday_on_or_before(start)
    n_cols = _column(end, first_sunday) + 1

    grid_width = n_cols * PITCH - GAP
    grid_bottom = GRID_TOP + 7 * PITCH - GAP
    width = GRID_LEFT + grid_width + 14
    height = grid_bottom + 40

    caption_raw = title if title is not None else _caption(activities)
    # Attribute values need quotes escaped too, unlike text nodes.
    caption_text = escape(caption_raw)
    caption_attr = escape(caption_raw, {'"': "&quot;", "'": "&apos;"})

    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}" '
            f'role="img" aria-label="{caption_attr}">'
        ),
        f'<rect width="{width}" height="{height}" fill="#ffffff" rx="6"/>',
        f'<text x="{GRID_LEFT}" y="14" font-size="12" fill="{_TEXT}" '
        f'font-family="Helvetica, Arial, sans-serif">{caption_text}</text>',
    ]

    for col, label in _month_labels(activities, first_sunday):
        x = GRID_LEFT + col * PITCH
        parts.append(
            f'<text x="{x}" y="34" font-size="10" fill="{_MUTED}" '
            f'font-family="Helvetica, Arial, sans-serif">{label}</text>'
        )

    for row, label in sorted(_WEEKDAY_LABELS.items()):
        y = GRID_TOP + row * PITCH + 9
        parts.append(
            f'<text x="{GRID_LEFT - 6}" y="{y}" font-size="10" fill="{_MUTED}" '
            f'text-anchor="end" '
            f'font-family="Helvetica, Arial, sans-serif">{label}</text>'
        )

    for activity in activities:
        x = GRID_LEFT + _column(activity.date, first_sunday) * PITCH
        y = GRID_TOP + _row(activity.date) * PITCH
        level = level_for(activity.commit_count)
        tooltip = escape(_tooltip(activity.commit_count, activity.date))
        parts.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
            f'fill="{LEVEL_COLORS[level]}" data-date="{activity.date.isoformat()}" '
            f'data-level="{level}"><title>{tooltip}</title></rect>'
        )

    # Legend, bottom-right: "Less [o o o o o] More".
    legend_width = 27 + 5 * PITCH - GAP + 6 + 28
    legend_x = GRID_LEFT + grid_width - legend_width
    legend_y = grid_bottom + 15
    parts.append(
        f'<text x="{legend_x}" y="{legend_y + 9}" font-size="10" fill="{_MUTED}" '
        f'font-family="Helvetica, Arial, sans-serif">Less</text>'
    )
    for i, color in enumerate(LEVEL_COLORS):
        x = legend_x + 27 + i * PITCH
        parts.append(
            f'<rect x="{x}" y="{legend_y}" width="{CELL}" height="{CELL}" '
            f'rx="2" fill="{color}"/>'
        )
    more_x = legend_x + 27 + 5 * PITCH - GAP + 6
    parts.append(
        f'<text x="{more_x}" y="{legend_y + 9}" font-size="10" fill="{_MUTED}" '
        f'font-family="Helvetica, Arial, sans-serif">More</text>'
    )

    parts.append("</svg>")
    return "\n".join(parts) + "\n"

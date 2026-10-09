"""SVG renderer tests: valid XML, cell counts, alignment, colors, wording."""

import xml.etree.ElementTree as ET
from datetime import date, timedelta

from gh_activity_forge.generator import DayActivity, generate_activity
from gh_activity_forge.svg import (
    GRID_LEFT,
    GRID_TOP,
    LEVEL_COLORS,
    PITCH,
    level_for,
    render_svg,
)

NS = "{http://www.w3.org/2000/svg}"


def _cells(root: ET.Element) -> list[ET.Element]:
    """Only data-bearing cells count — legend swatches are plain rects."""
    return [el for el in root.iter(f"{NS}rect") if el.get("data-date")]


def _texts(root: ET.Element) -> list[str]:
    return [el.text or "" for el in root.iter(f"{NS}text")]


def test_full_leap_year_svg_is_valid_xml_with_366_cells_and_53_columns() -> None:
    activities = generate_activity(
        date(2024, 1, 1), date(2024, 12, 31), "random", seed=42
    )
    root = ET.fromstring(render_svg(activities))  # raises if not valid XML
    cells = _cells(root)
    assert len(cells) == 366
    assert any(c.get("data-date") == "2024-02-29" for c in cells)
    assert len({c.get("x") for c in cells}) == 53  # 53 week columns
    for cell in cells:
        tooltip = cell.find(f"{NS}title")
        assert tooltip is not None and "contribution" in (tooltip.text or "")


def test_non_leap_year_has_365_cells() -> None:
    activities = generate_activity(
        date(2025, 1, 1), date(2025, 12, 31), "custom", seed=42
    )
    root = ET.fromstring(render_svg(activities))
    assert len(_cells(root)) == 365


def test_every_cell_sits_in_the_correct_weekday_row_and_week_column() -> None:
    activities = generate_activity(
        date(2026, 1, 1), date(2026, 12, 31), "streak", seed=42
    )
    root = ET.fromstring(render_svg(activities))
    first_sunday = date(2025, 12, 28)  # Sunday on/before 2026-01-01
    for cell in _cells(root):
        day = date.fromisoformat(cell.get("data-date", ""))
        expected_row = (day.weekday() + 1) % 7  # 0 = Sunday, GitHub layout
        expected_x = GRID_LEFT + ((day - first_sunday).days // 7) * PITCH
        assert int(cell.get("y", -1)) == GRID_TOP + expected_row * PITCH
        assert int(cell.get("x", -1)) == expected_x

    # The very first day of the range: 2026-01-01 is a Thursday -> row 4.
    first = next(
        c for c in _cells(root) if c.get("data-date") == "2026-01-01"
    )
    assert date(2026, 1, 1).weekday() == 3  # Thursday
    assert int(first.get("y", -1)) == GRID_TOP + 4 * PITCH


def test_color_bucket_boundaries_in_code_and_in_svg() -> None:
    assert level_for(0) == 0
    assert level_for(1) == 1
    assert level_for(2) == 1
    assert level_for(3) == 2
    assert level_for(5) == 2
    assert level_for(6) == 3
    assert level_for(9) == 3
    assert level_for(10) == 4
    assert level_for(12) == 4

    counts = [0, 1, 3, 6, 12]
    activities = [
        DayActivity(date(2026, 6, 1) + timedelta(days=i), n)
        for i, n in enumerate(counts)
    ]
    root = ET.fromstring(render_svg(activities))
    fills = {c.get("data-date"): c.get("fill") for c in _cells(root)}
    for i, n in enumerate(counts):
        day = (date(2026, 6, 1) + timedelta(days=i)).isoformat()
        assert fills[day] == LEVEL_COLORS[level_for(n)]
    # spot-check the exact GitHub palette values from the brief
    assert fills["2026-06-01"] == "#ebedf0"
    assert fills["2026-06-02"] == "#9be9a8"
    assert fills["2026-06-03"] == "#40c463"
    assert fills["2026-06-04"] == "#30a14e"
    assert fills["2026-06-05"] == "#216e39"


def test_tooltips_use_github_wording_with_correct_dates() -> None:
    activities = [
        DayActivity(date(2026, 3, 3), 1),   # a Tuesday
        DayActivity(date(2026, 3, 4), 14),  # a Wednesday
    ]
    root = ET.fromstring(render_svg(activities))
    titles = [t.text for t in root.iter(f"{NS}title")]
    assert "1 contribution on Tuesday, March 3, 2026" in titles
    assert "14 contributions on Wednesday, March 4, 2026" in titles


def test_caption_legend_labels_and_escaping() -> None:
    activities = generate_activity(
        date(2024, 1, 1), date(2024, 12, 31), "custom", seed=42
    )
    total = sum(a.commit_count for a in activities)

    # Default caption + all the chrome GitHub has.
    root = ET.fromstring(render_svg(activities))
    texts = _texts(root)
    assert f"{total:,} contributions in 2024" in texts
    assert "Less" in texts and "More" in texts
    for month in (
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ):
        assert month in texts
    for weekday in ("Mon", "Wed", "Fri"):
        assert weekday in texts

    # A hostile caption must still yield valid, escaped XML.
    hostile = 'Tom & Jerry\'s "green" <year>'
    root2 = ET.fromstring(render_svg(activities, title=hostile))
    assert hostile in _texts(root2)

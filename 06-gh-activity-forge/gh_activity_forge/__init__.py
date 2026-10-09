"""gh-activity-forge — a GitHub contribution-graph generator.

Given a date range and an intensity profile, produce a realistic-looking
contribution plan (pure data), render it as a hand-built SVG contribution
graph, and write JSON/Markdown/HTML reports. Optionally emit an opt-in
shell script that creates backdated demo commits (never for real work).
"""

from .generator import DayActivity, generate_activity, longest_streak
from .svg import render_svg

__all__ = [
    "DayActivity",
    "generate_activity",
    "longest_streak",
    "render_svg",
]
__version__ = "1.0.0"

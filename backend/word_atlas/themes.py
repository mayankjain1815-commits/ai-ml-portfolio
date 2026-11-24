"""Visual palette exposed by the API and consumed by index.html.

The previous festive skin is gone: one honest aurora palette now drives both
the canvas systems and the new solar-system view.
"""

PALETTE = {
    "aurora": {
        "id": "aurora",
        "name": "Aurora neon",
        "tagline": "Obsidian navy, electric cyan, hot magenta, acid lime, violet and ice.",
        "colors": {
            "bg": "#060918", "bg2": "#0d1430", "primary": "#2de7ff",
            "secondary": "#ff42c6", "accent": "#c4ff4d", "violet": "#8e64ff",
            "ice": "#e9f2ff",
        },
        "snow": False,
        "ornaments": False,
        "glyph": "✦",
    },
}


def all_themes():
    return [dict(theme) for theme in PALETTE.values()]


def get_theme(theme_id):
    theme = PALETTE.get(theme_id.lower())
    return dict(theme) if theme else None

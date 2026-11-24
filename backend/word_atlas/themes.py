"""Visual themes exposed by the API and consumed by index.html."""

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
    "christmas": {
        "id": "christmas",
        "name": "Christmas 2026",
        "tagline": "Snow, tree green, bauble red and gold — same systems, festive skin.",
        "colors": {
            "bg": "#07120d", "bg2": "#11291d", "primary": "#ff3b4e",
            "secondary": "#ffd166", "accent": "#39d98a", "violet": "#ff8a5b",
            "ice": "#f6fff8",
        },
        "snow": True,
        "ornaments": True,
        "glyph": "🎄",
    },
}


def all_themes():
    return [dict(theme) for theme in PALETTE.values()]


def get_theme(theme_id):
    theme = PALETTE.get(theme_id.lower())
    return dict(theme) if theme else None

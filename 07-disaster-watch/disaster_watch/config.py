"""Configuration for Disaster Watch.

Central place for colors, thresholds, paths and defaults. Keeps values explicit
so they are easy to read and adjust.
"""

from __future__ import annotations

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_ROOT / "data"
TEMPLATES_DIR = PACKAGE_ROOT / "templates"
STATIC_DIR = PACKAGE_ROOT / "static"
RUNS_DIR = PROJECT_ROOT / "runs"
DEFAULT_RUNS = RUNS_DIR / "latest"

# Color palette (as requested)
COLOR_ICE_SILVER_BG = "#f7f9fb"
COLOR_ICE_SILVER_CARD = "#ffffff"
COLOR_ICE_SILVER_DIVIDER = "#c9d2dc"
COLOR_ICE_SILVER_LINE = "#eef2f6"
COLOR_DEEP_AUBERGINE = "#2a1028"
COLOR_DEEP_AUBERGINE_PANEL = "#3b1d36"
COLOR_DEEP_AUBERGINE_ACCENT = "#4f2a45"
COLOR_MARIGOLD = "#f5b700"
COLOR_MARIGOLD_HOVER = "#ffcc33"
COLOR_MARIGOLD_DARK = "#d99a00"

# Risk thresholds (index 0-100)
RISK_LOW_MAX = 25
RISK_MOD_MAX = 50
RISK_HIGH_MAX = 75
# >= 75 -> critical in practice, but split by ranges

# Alert thresholds
RAIN_ALERT_MM_H = 30.0
WIND_ALERT_KPH = 65.0
PRESSURE_DROP_HPA = 6.0
HUMIDITY_HIGH_PCT = 90.0

# Alert dedup window (hours)
ALERT_DEDUP_HOURS = 6

# Simulation defaults
DEFAULT_HOURS = 72
DEFAULT_SEED = 13
DEFAULT_BATCH_HOURLY = True

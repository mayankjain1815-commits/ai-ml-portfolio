"""Time utilities for deterministic timestamps."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def now_utc() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(timezone.utc)


def fmt_iso(dt: datetime) -> str:
    """Format datetime as ISO8601 string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def hours_ago(hours: int) -> datetime:
    """Return datetime hours ago in UTC."""
    return now_utc() - timedelta(hours=hours)


def add_hours(dt: datetime, hours: int) -> datetime:
    """Add hours to datetime."""
    return dt + timedelta(hours=hours)

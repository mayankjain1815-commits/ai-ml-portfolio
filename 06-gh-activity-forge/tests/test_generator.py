"""Core-logic tests: date coverage, validation, determinism, profile behavior.

All assertions are on fixed seeds so they are stable forever.
"""

from datetime import date, timedelta

import pytest

from gh_activity_forge.generator import (
    generate_activity,
    longest_streak,
)

FULL_YEAR_2026 = (date(2026, 1, 1), date(2026, 12, 31))


def test_full_year_coverage_leap_vs_non_leap() -> None:
    """2024 (leap) yields 366 days incl. Feb 29; 2025 yields 365 without."""
    leap = generate_activity(date(2024, 1, 1), date(2024, 12, 31), "random")
    assert len(leap) == 366
    assert any(a.date == date(2024, 2, 29) for a in leap)

    plain = generate_activity(date(2025, 1, 1), date(2025, 12, 31), "random")
    assert len(plain) == 365
    assert not any(a.date.month == 2 and a.date.day == 29 for a in plain)

    for prev, curr in zip(leap, leap[1:]):
        assert curr.date - prev.date == timedelta(days=1)  # contiguous


def test_partial_range_is_exact_and_contiguous() -> None:
    start, end = date(2026, 3, 5), date(2026, 3, 19)
    activities = generate_activity(start, end, "custom", seed=1)
    assert [a.date for a in activities] == [
        start + timedelta(days=i) for i in range(15)
    ]


def test_start_after_end_raises() -> None:
    with pytest.raises(ValueError, match="after"):
        generate_activity(date(2026, 5, 1), date(2026, 4, 1), "random")


def test_over_five_years_and_unknown_profile_raise() -> None:
    with pytest.raises(ValueError, match="5-year"):
        generate_activity(date(2020, 1, 1), date(2026, 1, 1), "random")
    with pytest.raises(ValueError, match="unknown profile"):
        generate_activity(date(2026, 1, 1), date(2026, 12, 31), "chaos")


def test_same_seed_is_deterministic_different_seed_differs() -> None:
    a = generate_activity(*FULL_YEAR_2026, "random", seed=42)
    b = generate_activity(*FULL_YEAR_2026, "random", seed=42)
    c = generate_activity(*FULL_YEAR_2026, "random", seed=7)
    assert a == b
    assert a != c


def test_custom_profile_weekends_lighter_with_vacation_weeks() -> None:
    activities = generate_activity(*FULL_YEAR_2026, "custom", seed=42)
    weekday = [a.commit_count for a in activities if a.date.weekday() < 5]
    weekend = [a.commit_count for a in activities if a.date.weekday() >= 5]
    assert sum(weekday) / len(weekday) > sum(weekend) / len(weekend)

    # at least one full zero-commit week (a vacation gap), and no negatives
    longest_zero = best = 0
    for activity in activities:
        longest_zero = longest_zero + 1 if activity.commit_count == 0 else 0
        best = max(best, longest_zero)
    assert best >= 7
    assert min(a.commit_count for a in activities) >= 0


def test_streak_profile_produces_run_of_at_least_five() -> None:
    """Seeded statistical guarantee: streaks really do streak."""
    activities = generate_activity(*FULL_YEAR_2026, "streak", seed=42)
    assert longest_streak(activities) >= 5


def test_random_profile_has_bursts_zeros_and_valid_counts() -> None:
    activities = generate_activity(*FULL_YEAR_2026, "random", seed=42)
    counts = [a.commit_count for a in activities]
    assert min(counts) >= 0
    assert any(c == 0 for c in counts)  # quiet days happen
    assert max(counts) >= 10  # occasional burst day happens

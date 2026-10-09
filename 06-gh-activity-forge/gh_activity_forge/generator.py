"""Generate a plausible year of commit activity as plain data.

The generator is pure stdlib and fully deterministic for a given seed: it
turns (start, end, profile, seed) into a list of DayActivity values that the
SVG renderer, the reports and the git-script emitter all consume. Nothing in
here touches the filesystem or the network.

Why date math uses ``datetime.date`` and never timestamps: contribution
graphs are calendar objects, not instants. A "day" only makes sense in some
calendar and some timezone; using naive timestamps would silently shift days
across midnight (see README interview Q&A).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import date, timedelta

PROFILES: tuple[str, ...] = ("random", "streak", "custom")

#: Hard cap on the size of a generated range: 5 * 366 days (five years,
#: counting leap days). Longer ranges are rejected loudly instead of being
#: silently truncated — a wrong-but-short range is worse than an error.
MAX_DAYS = 5 * 366

#: How many whole "vacation" weeks (columns of zeros) to punch into a range
#: that is long enough to hold them. Zero-commit weeks are what make a graph
#: look human instead of machine-generated.
VACATION_WEEKS = 2


@dataclass(frozen=True)
class DayActivity:
    """One day's planned activity.

    A tuple of (date, commit_count) with names — frozen so downstream code
    can't mutate the plan after it has been generated.
    """

    date: date
    commit_count: int


def _poisson(rng: random.Random, lam: float) -> int:
    """Sample a Poisson variable with rate ``lam`` (Knuth's algorithm).

    Real commit counts are bursty around a low daily average, which a
    Poisson distribution models well: most days are small, a few days are
    big. ``lam`` must be >= 0.
    """
    if lam <= 0:
        return 0
    threshold = math.exp(-lam)
    k, p = 0, 1.0
    while True:
        p *= rng.random()
        if p <= threshold:
            return k
        k += 1


def _first_sunday_on_or_before(day: date) -> date:
    """Start of the week column that ``day`` falls into (Sunday-first rows)."""
    # datetime.date.weekday(): Monday=0 ... Sunday=6. Convert to Sunday=0.
    offset = (day.weekday() + 1) % 7
    return day - timedelta(days=offset)


def _pick_vacation_weeks(
    start: date, end: date, rng: random.Random
) -> set[date]:
    """Pick whole week-columns (Saturdays-free, Sunday..Saturday) to zero out.

    Only ranges of at least ~10 weeks get vacations: blanking a third of a
    two-week sample would look like a bug, not a holiday.
    """
    first_sunday = _first_sunday_on_or_before(start)
    last_sunday = _first_sunday_on_or_before(end)
    n_weeks = ((last_sunday - first_sunday).days // 7) + 1
    if n_weeks < 10:
        return set()
    # Stay away from the very first and very last column so the graph never
    # opens or closes on an unexplained blank.
    candidates = list(range(1, n_weeks - 1))
    picks = rng.sample(candidates, k=min(VACATION_WEEKS, len(candidates)))
    return {first_sunday + timedelta(weeks=w) for w in picks}


def _in_vacation(day: date, vacations: set[date], first_sunday: date) -> bool:
    """True if ``day`` falls inside one of the picked vacation columns."""
    column = first_sunday + timedelta(weeks=(day - first_sunday).days // 7)
    return column in vacations


def _generate_random(
    days: list[date], vacations: set[date], first_sunday: date, rng: random.Random
) -> list[int]:
    """Poisson-ish daily commits: quiet weekdays, quieter weekends, rare bursts."""
    counts: list[int] = []
    for day in days:
        if _in_vacation(day, vacations, first_sunday):
            counts.append(0)
            continue
        lam = 1.8 if day.weekday() < 5 else 0.8
        if rng.random() < 0.01:  # ~3-4 burst days a year
            lam *= 6.0
        counts.append(_poisson(rng, lam))
    return counts


def _generate_streak(
    days: list[date], vacations: set[date], first_sunday: date, rng: random.Random
) -> list[int]:
    """A few intense streaks on an otherwise quiet year.

    Background is sparse (mostly zeros), then 3-5 seeded streak windows of
    5-14 consecutive busy days are stamped on top. Windows are rejected if
    they would run through a vacation column, so every streak the user sees
    is a clean run — which is also what the streak-profile test asserts.
    """
    n = len(days)
    counts = [0] * n
    for i, day in enumerate(days):
        if _in_vacation(day, vacations, first_sunday):
            continue
        if rng.random() < 0.08:  # occasional lone 1-2 commit days between streaks
            counts[i] = rng.randint(1, 2)

    for _ in range(rng.randint(3, 5)):
        length = rng.randint(5, 14)
        if length > n:
            continue
        offset = 0
        for _attempt in range(50):  # rejection-sample a vacation-free window
            candidate = rng.randint(0, n - length)
            window = days[candidate : candidate + length]
            if not any(
                _in_vacation(d, vacations, first_sunday) for d in window
            ):
                offset = candidate
                break
        else:
            continue  # no clean window found; keep the year quieter instead
        for j in range(length):
            if rng.random() < 0.08:  # burst day inside the streak
                counts[offset + j] = rng.randint(10, 14)
            else:
                counts[offset + j] = rng.randint(3, 8)
    return counts


def _generate_custom(
    days: list[date], vacations: set[date], first_sunday: date, rng: random.Random
) -> list[int]:
    """Weekly rhythm: heavy weekdays, light weekends, vacation gaps, some bursts."""
    counts: list[int] = []
    for i, day in enumerate(days):
        if _in_vacation(day, vacations, first_sunday):
            counts.append(0)
            continue
        if day.weekday() < 5:
            if rng.random() < 0.15:  # an off day even midweek
                count = rng.randint(0, 2)
            else:
                count = rng.randint(4, 9)
            if rng.random() < 0.05:  # the occasional 10+ burst day
                count += rng.randint(6, 10)
        else:
            count = rng.randint(0, 2)
        counts.append(count)
    return counts


def generate_activity(
    start: date, end: date, profile: str, *, seed: int = 42
) -> list[DayActivity]:
    """Generate one DayActivity per day in [start, end] (inclusive).

    Args:
        start: first day of the range (inclusive).
        end: last day of the range (inclusive); must not be before ``start``.
        profile: one of ``PROFILES`` — 'random', 'streak' or 'custom'.
        seed: RNG seed; the same (range, profile, seed) always yields the
            identical plan, which is what makes the output testable.

    Returns:
        A list of DayActivity, one per day, in ascending date order.

    Raises:
        ValueError: start > end, unknown profile, or range > MAX_DAYS.
    """
    if profile not in PROFILES:
        raise ValueError(
            f"unknown profile {profile!r}; choose one of {', '.join(PROFILES)}"
        )
    if start > end:
        raise ValueError(
            f"start date {start.isoformat()} is after end date {end.isoformat()}"
        )
    span = (end - start).days + 1
    if span > MAX_DAYS:
        raise ValueError(
            f"range of {span} days is longer than the 5-year limit "
            f"({MAX_DAYS} days); pick a shorter range"
        )

    days = [start + timedelta(days=i) for i in range(span)]
    rng = random.Random(seed)
    first_sunday = _first_sunday_on_or_before(start)
    vacations = _pick_vacation_weeks(start, end, rng)

    if profile == "random":
        counts = _generate_random(days, vacations, first_sunday, rng)
    elif profile == "custom":
        counts = _generate_custom(days, vacations, first_sunday, rng)
    else:  # streak
        counts = _generate_streak(days, vacations, first_sunday, rng)

    assert len(counts) == len(days), "generator must emit exactly one count per day"
    return [DayActivity(d, c) for d, c in zip(days, counts)]


def longest_streak(activities: list[DayActivity]) -> int:
    """Longest run of consecutive days with at least one commit."""
    longest = current = 0
    for activity in activities:
        if activity.commit_count > 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def total_commits(activities: list[DayActivity]) -> int:
    """Sum of every commit in the plan."""
    return sum(a.commit_count for a in activities)

"""Command-line interface for gh-activity-forge.

``python -m gh_activity_forge --help`` is the front door: it documents both
date-input styles (``--year`` vs ``--from/--to``), the profiles, the seed,
and — loudly — what ``--emit-git-script`` actually does.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from .generator import PROFILES, generate_activity, total_commits
from .report import month_totals, write_outputs

_EPILOG = """\
examples:
  python -m gh_activity_forge --year 2026
  python -m gh_activity_forge --year 2024 --profile streak --seed 7
  python -m gh_activity_forge --from 2026-03-01 --to 2026-08-31 --profile custom
  python -m gh_activity_forge --year 2026 --output ./out --emit-git-script

notes:
  Same seed + same range + same profile => bit-identical output.
  Ranges longer than 5 years are rejected. --emit-git-script additionally
  writes fake_commits.sh, which creates BACKDATED demo commits — read the
  warning inside that file before ever running it.
"""


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser (separated out so tests can introspect it)."""
    parser = argparse.ArgumentParser(
        prog="gh-activity-forge",
        description=(
            "Generate a realistic-looking GitHub contribution plan for a year "
            "or date range and render it as a hand-built SVG contribution "
            "graph. Fully offline, deterministic under --seed."
        ),
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    dates = parser.add_argument_group("date range")
    exclusive = dates.add_mutually_exclusive_group()
    exclusive.add_argument(
        "--year",
        type=int,
        metavar="YYYY",
        help="generate the full calendar year (Jan 1 to Dec 31)",
    )
    exclusive.add_argument(
        "--from",
        dest="from_date",
        metavar="YYYY-MM-DD",
        help="first day of a custom range (requires --to)",
    )
    dates.add_argument(
        "--to",
        metavar="YYYY-MM-DD",
        help="last day of a custom range (only valid with --from)",
    )

    parser.add_argument(
        "--profile",
        choices=PROFILES,
        default="random",
        help=(
            "activity style: 'random' = Poisson-ish daily commits, "
            "'streak' = intense streaks on a quiet year, "
            "'custom' = heavy weekdays / light weekends + vacations "
            "(default: random)"
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="RNG seed; the same seed always produces the same plan "
        "(default: 42)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("out"),
        metavar="DIR",
        help="directory for the generated files (default: ./out)",
    )
    parser.add_argument(
        "--emit-git-script",
        action="store_true",
        help="ALSO write fake_commits.sh, a script that creates fake "
        "backdated commits for demo repos — read its warning header first "
        "(default: off; you get SVG/JSON/Markdown/HTML only)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress the console preview and the list of written files",
    )
    return parser


def _parse_iso_date(parser: argparse.ArgumentParser, raw: str, flag: str) -> date:
    """Parse a YYYY-MM-DD string, turning any failure into a usage error."""
    try:
        return date.fromisoformat(raw)
    except ValueError:
        parser.error(
            f"{flag} expects an ISO date (YYYY-MM-DD), got {raw!r}"
        )
        raise  # unreachable: parser.error always exits


def _resolve_range(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> tuple[date, date]:
    """Turn --year / --from / --to into an inclusive (start, end) pair."""
    if args.year is not None:
        if not 1 <= args.year <= 9999:
            parser.error(f"--year must be between 1 and 9999, got {args.year}")
        if args.to is not None:
            parser.error("--to cannot be combined with --year (use --from/--to)")
        return date(args.year, 1, 1), date(args.year, 12, 31)
    if args.from_date is not None:
        if args.to is None:
            parser.error("--from requires --to (both ends of a custom range)")
        start = _parse_iso_date(parser, args.from_date, "--from")
        end = _parse_iso_date(parser, args.to, "--to")
        return start, end
    if args.to is not None:
        parser.error("--to requires --from")
    today = date.today()
    return date(today.year, 1, 1), date(today.year, 12, 31)


def _print_preview(
    activities: list, out_paths: list[Path], *, profile: str, seed: int
) -> None:
    """Small ASCII month-by-month bar chart plus the list of written files."""
    total = total_commits(activities)
    active = sum(1 for a in activities if a.commit_count > 0)
    start, end = activities[0].date, activities[-1].date
    print(
        f"Planned {start.isoformat()} to {end.isoformat()} "
        f"({len(activities)} days) · profile {profile} · seed {seed}"
    )
    print(f"Total: {total:,} commits on {active} active days")

    months = month_totals(activities)
    peak = max((c for _, c, _ in months), default=0)
    print("\nMonth-by-month commits")
    for key, commits, _active in months:
        bar_len = round(commits / peak * 24) if peak else 0
        if commits > 0 and bar_len == 0:
            bar_len = 1
        print(f"  {key} |{'#' * bar_len:<24} {commits:>5}")

    print("\nWrote:")
    for path in out_paths:
        print(f"  {path}")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    start, end = _resolve_range(parser, args)

    try:
        activities = generate_activity(
            start, end, args.profile, seed=args.seed
        )
    except ValueError as exc:
        parser.error(str(exc))

    try:
        out_paths = write_outputs(
            args.output,
            activities,
            profile=args.profile,
            seed=args.seed,
            emit_git_script=args.emit_git_script,
        )
    except ValueError as exc:
        parser.error(str(exc))

    if not args.quiet:
        _print_preview(activities, out_paths, profile=args.profile, seed=args.seed)
    return 0

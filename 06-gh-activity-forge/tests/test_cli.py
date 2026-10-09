"""CLI tests: help quality, end-to-end run into tmp_path, usage errors."""

from datetime import date

import pytest

from gh_activity_forge.cli import build_parser, main


def test_help_is_excellent() -> None:
    help_text = build_parser().format_help()
    for needle in (
        "--year",
        "--from",
        "--to",
        "--profile",
        "--seed",
        "--output",
        "--emit-git-script",
        "--quiet",
        "examples:",
        "fake_commits.sh",
    ):
        assert needle in help_text


def test_end_to_end_run_writes_files_and_quiet_is_quiet(
    tmp_path, capsys
) -> None:
    code = main(
        ["--year", "2026", "--profile", "custom", "--output", str(tmp_path)]
    )
    assert code == 0
    captured = capsys.readouterr()
    assert "Month-by-month commits" in captured.out
    assert "contribution.svg" in captured.out

    for name in (
        "contribution.svg",
        "activity.json",
        "summary.md",
        "report.html",
    ):
        assert (tmp_path / name).exists()

    assert main(
        [
            "--from", "2026-01-01", "--to", "2026-01-31",
            "--output", str(tmp_path / "quiet"),
            "--quiet",
        ]
    ) == 0
    assert capsys.readouterr().out == ""
    assert (tmp_path / "quiet" / "summary.md").exists()


def test_usage_errors_exit_with_code_2(tmp_path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(
            ["--from", "2026-05-01", "--to", "2026-04-01",
             "--output", str(tmp_path)]
        )
    assert excinfo.value.code == 2

    with pytest.raises(SystemExit) as excinfo:
        main(["--year", "2026", "--to", "2026-12-31"])
    assert excinfo.value.code == 2

    with pytest.raises(SystemExit) as excinfo:
        main(["--from", "2026-01-01"])  # --to required
    assert excinfo.value.code == 2


def test_default_range_is_current_year() -> None:
    # No date flags at all: CLI falls back to today's calendar year.
    from gh_activity_forge.cli import _resolve_range

    parser = build_parser()
    args = parser.parse_args([])
    start, end = _resolve_range(parser, args)
    today = date.today()
    assert (start, end) == (date(today.year, 1, 1), date(today.year, 12, 31))

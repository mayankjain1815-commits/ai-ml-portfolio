"""Output-artifact tests: files, JSON structure, summary, offline HTML."""

import json
from datetime import date

from gh_activity_forge.generator import generate_activity, total_commits
from gh_activity_forge.report import busiest_day, month_totals, write_outputs


def test_write_outputs_writes_every_artifact_with_correct_totals(tmp_path) -> None:
    activities = generate_activity(
        date(2026, 1, 1), date(2026, 12, 31), "random", seed=42
    )
    paths = write_outputs(
        tmp_path, activities, profile="random", seed=42, emit_git_script=True
    )
    assert [p.name for p in paths] == [
        "contribution.svg",
        "activity.json",
        "summary.md",
        "report.html",
        "fake_commits.sh",
    ]
    for path in paths:
        assert path.exists() and path.stat().st_size > 0

    data = json.loads((tmp_path / "activity.json").read_text())
    assert data["profile"] == "random"
    assert data["seed"] == 42
    assert data["range"] == {
        "start": "2026-01-01",
        "end": "2026-12-31",
        "days": 365,  # 2026 is not a leap year
    }
    assert data["totals"]["commits"] == total_commits(activities)
    assert len(data["per_day"]) == 365
    busiest = busiest_day(activities)
    assert data["totals"]["busiest_day"] == {
        "date": busiest.date.isoformat(),
        "commits": busiest.commit_count,
    }

    summary = (tmp_path / "summary.md").read_text()
    assert "**Total commits:**" in summary
    assert "**Busiest day:**" in summary
    assert "**Longest streak:**" in summary
    assert summary.count("| 2026-") == 12  # one row per month

    html = (tmp_path / "report.html").read_text()
    assert "<svg" in html and "</svg>" in html  # SVG embedded inline
    assert "<script" not in html and "<link" not in html  # no CDN, no JS
    assert "random" in html and "seed 42" in html


def test_git_script_only_written_when_explicitly_requested(tmp_path) -> None:
    activities = generate_activity(
        date(2026, 1, 1), date(2026, 2, 1), "custom", seed=1
    )
    paths = write_outputs(tmp_path, activities, profile="custom", seed=1)
    assert [p.name for p in paths] == [
        "contribution.svg",
        "activity.json",
        "summary.md",
        "report.html",
    ]
    assert not (tmp_path / "fake_commits.sh").exists()


def test_regenerating_without_opt_in_removes_our_own_stale_script(tmp_path) -> None:
    activities = generate_activity(
        date(2026, 1, 1), date(2026, 2, 1), "custom", seed=1
    )
    write_outputs(tmp_path, activities, profile="custom", seed=1, emit_git_script=True)
    assert (tmp_path / "fake_commits.sh").exists()

    write_outputs(tmp_path, activities, profile="custom", seed=1)
    assert not (tmp_path / "fake_commits.sh").exists()

    # A same-named file we did NOT generate must survive untouched.
    foreign = tmp_path / "fake_commits.sh"
    foreign.write_text("#!/usr/bin/env bash\necho hello\n")
    write_outputs(tmp_path, activities, profile="custom", seed=1)
    assert foreign.exists()


def test_month_totals_aggregate_per_calendar_month() -> None:
    activities = generate_activity(
        date(2026, 2, 10), date(2026, 3, 5), "custom", seed=3
    )
    months = month_totals(activities)
    assert [key for key, _, _ in months] == ["2026-02", "2026-03"]
    total = sum(commits for _, commits, _ in months)
    assert total == total_commits(activities)
    assert all(active > 0 or commits == 0 for _, commits, active in months)

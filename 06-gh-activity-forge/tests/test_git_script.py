"""Git-script emitter tests: warnings, env vars, counts, shell quoting."""

import re
import shlex
import shutil
import subprocess
from datetime import date

import pytest

from gh_activity_forge.generator import DayActivity, generate_activity, total_commits
from gh_activity_forge.git_script import render_git_script, write_git_script


def _assert_valid_bash(path) -> None:
    """Syntax-check the script without executing a single line of it."""
    if not shutil.which("bash"):  # pragma: no cover
        pytest.skip("bash not available")
    result = subprocess.run(
        ["bash", "-n", str(path)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr


def test_script_carries_warning_header_env_vars_and_correct_commit_count(
    tmp_path,
) -> None:
    activities = generate_activity(
        date(2026, 1, 1), date(2026, 3, 31), "streak", seed=42
    )
    text = render_git_script(activities, profile="streak", seed=42)

    # Loud, honest header.
    assert text.startswith("#!/usr/bin/env bash")
    assert "FAKE, BACKDATED COMMITS" in text
    assert "NEVER push" in text
    assert "green squares" in text
    assert "set -euo pipefail" in text

    # One backdated commit per planned count, on the right days.
    total = total_commits(activities)
    stamps = re.findall(
        r"^GIT_AUTHOR_DATE=(\S+) GIT_COMMITTER_DATE=", text, re.MULTILINE
    )
    assert len(stamps) == total
    assert text.count("git commit --allow-empty") == total
    assert "GIT_COMMITTER_DATE=" in text
    iso_stamp = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    assert all(re.fullmatch(iso_stamp, s) for s in stamps)
    active_dates = {
        a.date.isoformat() for a in activities if a.commit_count > 0
    }
    assert {s[:10] for s in stamps} <= active_dates

    path = write_git_script(tmp_path / "fake_commits.sh", activities)
    assert path.stat().st_mode & 0o111  # executable bit set
    _assert_valid_bash(path)


def test_script_is_valid_bash_even_with_tricky_messages(tmp_path) -> None:
    """Apostrophes, quotes and dollar signs must not break the shell."""
    activities = [DayActivity(date(2026, 4, 1), 2)]
    messages = ("feat: don't break 'quotes' or $HOME",)
    text = render_git_script(activities, messages=messages)
    # Every message goes through shlex.quote, so nothing can escape the string.
    quoted_message = shlex.quote(messages[0])
    assert text.count(f"git commit --allow-empty -q -m {quoted_message}") == 2

    path = tmp_path / "tricky.sh"
    path.write_text(text, encoding="utf-8")
    _assert_valid_bash(path)


def test_script_is_deterministic_for_a_given_seed() -> None:
    activities = generate_activity(
        date(2026, 1, 1), date(2026, 2, 28), "random", seed=42
    )
    first = render_git_script(activities, seed=42)
    second = render_git_script(activities, seed=42)
    assert first == second

"""End-to-end CLI tests — every subcommand a user can type."""

import pytest

from skill_forge.cli import main


def test_list_prints_table(capsys):
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "csv-analyzer" in out
    assert "MODE" in out and "RISK" in out


def test_search_ranks_and_explains(capsys):
    assert main(["search", "convert km to miles"]) == 0
    out = capsys.readouterr().out
    assert "unit-convert" in out.splitlines()[1] or "Best match: unit-convert" in out


def test_pick_with_reasoning(capsys):
    assert main(["pick", "summarize this article"]) == 0
    out = capsys.readouterr().out
    assert "summarize-text" in out
    assert "confidence" in out


def test_pack_prints_bounded_prompt(capsys):
    assert main(["pack", "--task", "run the unit converter", "--budget", "800"]) == 0
    out = capsys.readouterr().out
    assert "tokens:" in out
    assert "SKILL:" in out


def test_pack_rejects_impossible_budget(capsys):
    assert main(["pack", "--task", "x", "--budget", "10"]) == 2
    assert "error" in capsys.readouterr().err


def test_run_action_skill(capsys):
    code = main([
        "run", "unit-convert",
        "--input", "value=12.5", "--input", "from_unit=km", "--input", "to_unit=miles",
    ])
    assert code == 0
    out = capsys.readouterr().out
    assert "7.767 miles" in out
    assert "action (deterministic)" in out


def test_run_unknown_skill_fails_cleanly(capsys):
    assert main(["run", "no-such-skill"]) == 2
    assert "error" in capsys.readouterr().err


def test_run_bad_input_format(capsys):
    assert main(["run", "unit-convert", "--input", "broken"]) == 2
    assert "key=value" in capsys.readouterr().err


def test_show_prints_body(capsys):
    assert main(["show", "debug-helper"]) == 0
    out = capsys.readouterr().out
    assert "Reproduce." in out
    assert "mode=guided" in out


def test_install_and_force(tmp_path, capsys):
    src = tmp_path / "my-skill"
    src.mkdir()
    (src / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: A test skill.\n---\nBody.",
        encoding="utf-8",
    )
    target = tmp_path / "target"

    assert main(["install", str(src), "--target", str(target)]) == 0
    assert (target / "my-skill" / "SKILL.md").exists()

    # Second install without --force must refuse...
    assert main(["install", str(src), "--target", str(target)]) == 2
    assert "--force" in capsys.readouterr().err
    # ...and succeed with it.
    assert main(["install", str(src), "--target", str(target), "--force"]) == 0


def test_install_rejects_invalid_skill(tmp_path, capsys):
    src = tmp_path / "broken"
    src.mkdir()
    (src / "SKILL.md").write_text("no frontmatter", encoding="utf-8")
    assert main(["install", str(src), "--target", str(tmp_path / "t")]) == 2
    assert "invalid skill" in capsys.readouterr().err


def test_install_requires_skill_md(tmp_path, capsys):
    src = tmp_path / "empty"
    src.mkdir()
    assert main(["install", str(src), "--target", str(tmp_path / "t")]) == 2
    assert "SKILL.md" in capsys.readouterr().err


def test_demo_runs_end_to_end(capsys):
    assert main(["demo"]) == 0
    out = capsys.readouterr().out
    assert "SKILL FORGE" in out
    assert "picked:" in out
    assert "ran via:" in out


def test_help_works():
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0

"""Tests for the command-line interface (offline demo mode, no argv side effects)."""

from crew_engine.cli import build_parser, main


def test_parser_exposes_all_commands():
    parser = build_parser()
    for command in ("report", "supervise", "demo"):
        sub = [a for a in parser._actions if getattr(a, "dest", None) == "command"]  # noqa: SLF001
        assert sub[0].choices is not None and command in sub[0].choices


def test_demo_runs_all_three_patterns_offline(capsys):
    code = main(["demo"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Sequential pipeline" in out
    assert "Supervisor crew" in out
    assert "Reflective crew" in out
    assert "refinements:" in out
    assert "[demo mode]" in out, "no-key runs must announce demo mode"


def test_demo_trace_prints_audit_log(capsys):
    main(["demo", "--trace"])
    out = capsys.readouterr().out
    assert "AGENT [Aria]" in out
    assert "AGENT [Cleo]" in out


def test_report_converges_to_how_it_works(capsys):
    code = main(["report", "How do neural networks work?"])
    out = capsys.readouterr().out
    assert code == 0
    assert "How it works" in out
    assert "refinements: 1" in out


def test_report_uses_default_topic_when_missing(capsys):
    main(["report"])
    out = capsys.readouterr().out
    assert "How do neural networks work?" in out


def test_supervise_produces_briefing(capsys):
    code = main(["supervise", "Summarize the history of AI"])
    out = capsys.readouterr().out
    assert code == 0
    assert "tasks executed:" in out
    assert out.count("- ") >= 1  # briefing bullets from the board facts
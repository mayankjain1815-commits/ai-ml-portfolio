"""Tests for the tool layer: calculator safety, file reading guardrails,
the app allowlist, offline web search, and the note tools."""

import sys

import pytest

from orbit_voice_assistant.memory import NotesStore
from orbit_voice_assistant.tools import (
    APP_ALLOWLIST,
    calculator,
    default_registry,
    open_app,
    read_file,
    web_search,
)


# ---------------------------------------------------------------- calculator
def test_calc_basics():
    assert calculator("2+2") == "2+2 = 4"
    assert calculator("10 % 3") == "10 % 3 = 1"
    assert calculator("(1 + 2) * 3") == "(1 + 2) * 3 = 9"
    assert calculator("2^10") == "2^10 = 1024"
    assert calculator("-5 + 3") == "-5 + 3 = -2"
    assert "6" in calculator("2 + 2 * 2")  # operator precedence from ast


def test_calc_division_by_zero_is_handled():
    out = calculator("1/0")
    assert "zero" in out.lower()


def test_calc_rejects_names_and_calls():
    out = calculator("__import__('os')")
    assert "handle numbers" in out
    out = calculator("2 + abs(-3)")
    assert "handle numbers" in out


def test_calc_caps_huge_exponents():
    assert "too large" in calculator("2**100000")
    assert "too large" in calculator("2^100000")


def test_calc_rejects_garbage():
    assert "handle numbers" in calculator("hello world")


# ---------------------------------------------------------------- read_file
def test_read_file_bundled():
    out = read_file("quick-tips")
    assert "Start small" in out
    assert "--- quick-tips.md ---" in out


def test_read_file_rejects_traversal():
    out = read_file("../.env")
    assert "not allowed" in out or "no file named" in out
    assert ".env" not in out  # never echo the attempted path content


def test_read_file_unknown_lists_bundled():
    out = read_file("nope")
    assert "no file named" in out
    assert "quick-tips" in out


# ---------------------------------------------------------------- open_app
def test_open_app_rejects_unknown_without_subprocess(monkeypatch):
    import orbit_voice_assistant.tools as tools

    calls = []
    monkeypatch.setattr(tools.subprocess, "run", lambda *a, **k: calls.append(a))
    out = open_app("tiktok")
    assert "not on my allowlist" in out
    assert calls == []
    assert "calculator" in APP_ALLOWLIST


def test_open_app_only_runs_on_macos(monkeypatch):
    import orbit_voice_assistant.tools as tools

    monkeypatch.setattr(tools.platform, "system", lambda: "Linux")
    out = open_app("calculator")
    assert "only wired up on macOS" in out


def test_open_app_launches_allowlisted_app(monkeypatch):
    import orbit_voice_assistant.tools as tools

    calls = []
    monkeypatch.setattr(tools.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(tools.subprocess, "run",
                        lambda args, **kw: calls.append(args) or type("R", (), {})())
    out = open_app("calculator")
    assert "launching Calculator" in out
    assert calls and "Calculator" in calls[0]


# ---------------------------------------------------------------- web_search
def test_web_search_offline_falls_back(monkeypatch):
    class Fake:
        def get(self, *a, **k):
            raise RuntimeError("offline")

    monkeypatch.setitem(sys.modules, "requests", Fake())
    out = web_search("anything")
    assert "offline or blocked" in out


# ---------------------------------------------------------------- note tools
def test_note_tools_roundtrip(tmp_path):
    store = NotesStore(tmp_path / "notes.json")
    reg = default_registry(store)
    assert "Saved note" in reg.get("add_note")(text="buy milk")
    assert "buy milk" in reg.get("list_notes")()
    assert "Deleted" in reg.get("delete_note")(key="#1")
    assert "no notes yet" in reg.get("list_notes")()
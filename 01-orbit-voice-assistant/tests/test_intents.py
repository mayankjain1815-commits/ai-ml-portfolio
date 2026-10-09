"""Tests for the demo NLU brain: intent classification, slot extraction,
dispatch order (the rules are ordered on purpose), and tool wiring."""

import pytest

from orbit_voice_assistant.intents import DemoBrain


@pytest.fixture
def brain(registry):
    reg, _store = registry
    return DemoBrain(reg)


def _launch_recorder(monkeypatch):
    """Never really `open` an app in tests — record the call instead."""
    import orbit_voice_assistant.tools as tools

    calls = []
    monkeypatch.setattr(tools, "platform", type("P", (), {"system": staticmethod(lambda: "Darwin")})())
    monkeypatch.setattr(tools.subprocess, "run", lambda args, **kw: calls.append(args) or type("R", (), {})())
    return calls


def test_identity(brain):
    intent, reply, used = brain.run("who are you")
    assert intent == "identity"
    assert "Orbit" in reply
    assert used == []


def test_help(brain):
    intent, reply, _ = brain.run("what can you do")
    assert intent == "help"
    assert "math" in reply


def test_time(brain):
    intent, reply, used = brain.run("what time is it")
    assert intent == "time"
    assert used == ["current_time"]
    assert "It is" in reply
    assert str(__import__("datetime").datetime.now().year) in reply


def test_math_with_trigger(brain):
    intent, reply, used = brain.run("what is 12 * 8")
    assert intent == "math"
    assert used == ["calculator"]
    assert "96" in reply


def test_math_bare_expression(brain):
    intent, reply, _ = brain.run("2+2")
    assert intent == "math"
    assert "4" in reply


def test_math_beats_greet_when_both_present(brain):
    intent, reply, _ = brain.run("hi, what is 5 + 5")
    assert intent == "math"
    assert "10" in reply


def test_identity_beats_math_lookalike(brain):
    intent, reply, _ = brain.run("what is your name")
    assert intent == "identity"


def test_notes_add_and_lookup(brain, registry):
    _reg, store = registry
    intent, reply, used = brain.run("remember that Friday is the demo")
    assert intent == "notes_add"
    assert used == ["add_note"]
    assert len(store.list()) == 1
    assert store.list()[0]["text"] == "Friday is the demo"

    intent, reply, used = brain.run("list my notes")
    assert intent == "notes_lookup"
    assert "Friday is the demo" in reply


def test_notes_delete_by_index(brain, registry):
    _reg, store = registry
    brain.run("remember that Friday is the demo")
    intent, reply, _ = brain.run("delete note #1")
    assert intent == "notes_delete"
    assert len(store.list()) == 0


def test_open_app_allowlist(brain, registry, monkeypatch):
    calls = _launch_recorder(monkeypatch)
    intent, reply, used = brain.run("open calculator")
    assert intent == "open_app"
    assert used == ["open_app"]
    assert len(calls) == 1 and "Calculator" in calls[0]


def test_open_app_rejects_unknown(brain, monkeypatch):
    calls = _launch_recorder(monkeypatch)
    intent, reply, _ = brain.run("open tiktok")
    assert intent == "open_app"
    assert "not on my allowlist" in reply
    assert calls == []


def test_read_file(brain):
    intent, reply, used = brain.run("read quick-tips")
    assert intent == "read_file"
    assert used == ["read_file"]
    assert "Start small" in reply


def test_web_search_offline_is_graceful(brain, no_network):
    intent, reply, used = brain.run("search for RAG pipelines")
    assert intent == "web_search"
    assert used == ["web_search"]
    assert "offline or blocked" in reply


def test_fallback_for_gibberish(brain):
    intent, reply, _ = brain.run("blorp zzz")
    assert intent == "fallback"
    assert "help" in reply.lower()
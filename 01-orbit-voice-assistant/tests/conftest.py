"""Shared fixtures for Orbit tests: a fake ``requests`` so no test ever
touches the network, plus a helper that builds a registry on a tmp store."""

import sys

import pytest


class _NoNetwork:
    """Raises for any method — web_search/llm code paths see "offline"."""

    def get(self, *args, **kwargs):
        raise RuntimeError("network blocked in tests")

    post = get


@pytest.fixture
def no_network(monkeypatch):
    monkeypatch.setitem(sys.modules, "requests", _NoNetwork())
    return _NoNetwork()


@pytest.fixture
def registry(tmp_path):
    """A ToolRegistry wired to a fresh notes store under tmp_path."""
    from orbit_voice_assistant.memory import NotesStore
    from orbit_voice_assistant.tools import default_registry

    store = NotesStore(tmp_path / "notes.json")
    return default_registry(store), store
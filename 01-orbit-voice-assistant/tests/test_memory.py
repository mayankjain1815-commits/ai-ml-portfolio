"""Tests for the two memory layers: the persistent notes store and the
per-session ring buffer."""

from orbit_voice_assistant.memory import NotesStore, SessionMemory


def test_notes_store_persists_to_disk(tmp_path):
    path = tmp_path / "notes.json"
    store = NotesStore(path)
    note = store.add("remember the demo")
    assert note["id"]

    reloaded = NotesStore(path)  # fresh instance reads the same file
    assert len(reloaded.list()) == 1
    assert reloaded.list()[0]["text"] == "remember the demo"


def test_notes_store_delete_by_id(tmp_path):
    store = NotesStore(tmp_path / "notes.json")
    note = store.add("alpha")
    assert store.delete(note["id"])
    assert len(store) == 0
    assert not store.delete(note["id"])  # already gone


def test_notes_store_delete_by_index_and_substring(tmp_path):
    store = NotesStore(tmp_path / "notes.json")
    store.add("buy milk")
    store.add("call doctor")
    assert store.delete("#1")
    assert [n["text"] for n in store.list()] == ["call doctor"]
    assert store.delete("doctor")
    assert len(store) == 0


def test_notes_store_survives_corrupt_file(tmp_path):
    path = tmp_path / "notes.json"
    path.write_text("{not json", encoding="utf-8")
    store = NotesStore(path)
    assert len(store) == 0
    store.add("still works")
    assert len(store.list()) == 1


def test_session_memory_ring_buffer():
    session = SessionMemory(max_turns=2)
    for i in range(4):
        session.add(f"q{i}", f"a{i}")
    assert len(session.turns) == 2
    assert session.turns[0] == ("q2", "a2")  # oldest surviving turn
    assert "q3" in session.as_text()


def test_session_memory_empty_text():
    assert SessionMemory().as_text() == "(no prior turns)"
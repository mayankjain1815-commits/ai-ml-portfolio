"""End-to-end tests through the Flask test client (offline, no real HTTP)."""

import pytest

from orbit_voice_assistant.app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(notes_path=tmp_path / "notes.json")
    app.config["TESTING"] = True
    return app.test_client()


def test_index_serves_frontend(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Orbit" in html
    assert "/static/app.js" in html


def test_static_assets_served(client):
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200


def test_mode_is_demo_without_key(client):
    data = client.get("/api/mode").get_json()
    assert data["mode"] == "demo"
    assert "demo mode" in data["demo_note"]


def test_chat_math_end_to_end(client):
    resp = client.post("/api/chat", json={"message": "what is 6 * 7", "session_id": "s1"})
    data = resp.get_json()
    assert data["intent"] == "math"
    assert "42" in data["reply"]
    assert data["mode"] == "demo"
    assert data["tools_used"] == ["calculator"]
    assert data["session_id"] == "s1"


def test_chat_notes_persist_across_turns(client):
    client.post("/api/chat", json={"message": "remember that demo is Friday", "session_id": "s1"})
    resp = client.post("/api/chat", json={"message": "list my notes", "session_id": "s1"})
    assert "demo is Friday" in resp.get_json()["reply"]
    notes = client.get("/api/notes").get_json()["notes"]
    assert len(notes) == 1


def test_chat_generates_session_id(client):
    data = client.post("/api/chat", json={"message": "hello"}).get_json()
    assert data["session_id"]
    assert data["intent"] in {"greet", "fallback"}


def test_chat_rejects_empty_message(client):
    data = client.post("/api/chat", json={"message": "   "}).get_json()
    assert data["intent"] == "empty"


def test_chat_graceful_without_json_body(client):
    data = client.post("/api/chat", data="", content_type="application/json").get_json()
    assert data["intent"] == "empty"
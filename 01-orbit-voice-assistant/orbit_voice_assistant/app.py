"""Flask application — the browser frontend talks to these endpoints.

* ``GET  /``          -> the Web Speech API frontend (offline, no CDN)
* ``POST /api/chat``  -> {message, session_id} -> {reply, intent, mode, tools_used}
* ``GET  /api/mode``  -> which brain is active ("demo" | "llm")
* ``GET  /api/notes`` -> the saved notes (for the frontend's note panel)
"""

from __future__ import annotations

import uuid

from flask import Flask, jsonify, request

from .chat import handle_message
from .memory import NotesStore, SessionMemory
from .tools import ToolRegistry, default_registry


def create_app(
    notes_path=None,
    registry: ToolRegistry | None = None,
) -> Flask:
    app = Flask(
        __name__,
        static_folder="static",
        static_url_path="/static",
    )
    store = NotesStore(notes_path) if notes_path else NotesStore()
    reg = registry or default_registry(store)
    sessions: dict[str, SessionMemory] = {}

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    @app.get("/api/mode")
    def mode():
        from . import llm

        return jsonify({"mode": "llm" if llm.have_key() else "demo",
                        "demo_note": llm.demo_note()})

    @app.post("/api/chat")
    def chat():
        data = request.get_json(silent=True) or {}
        message = (data.get("message") or "").strip()
        session_id = data.get("session_id") or uuid.uuid4().hex
        session = sessions.setdefault(session_id, SessionMemory())
        if not message:
            return jsonify({"reply": "Say something first!", "intent": "empty",
                            "mode": "demo", "tools_used": [], "session_id": session_id})
        result = handle_message(message, session, store, reg)
        result["session_id"] = session_id
        return jsonify(result)

    @app.get("/api/notes")
    def notes():
        return jsonify({"notes": store.list()})

    return app
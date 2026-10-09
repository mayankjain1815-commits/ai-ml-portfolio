"""The chat pipeline: one message in, a reply out.

    message + session memory
        -> demo brain (rule-based NLU)   OR
           LLM brain (Gemini in a bounded ReAct tool loop, honest fallback)
        -> {reply, intent, mode, tools_used}

Both brains share the same :class:`ToolRegistry`, so the frontend and tests
see identical behaviour regardless of mode — the demo brain is a parallel
implementation of the same pipeline.
"""

from __future__ import annotations

import json
import re

from . import llm
from .intents import DemoBrain
from .memory import NotesStore, SessionMemory
from .tools import ToolRegistry


def _system_prompt(registry: ToolRegistry, session: SessionMemory, store: NotesStore) -> str:
    notes = store.list()
    notes_text = "\n".join(f"- {n['text']}" for n in notes[-8:]) or "- (no notes yet)"
    return (
        "You are Orbit, a friendly voice-first assistant. Reply briefly and "
        "conversationally, as if speaking aloud — short sentences, no markdown.\n\n"
        f"Your notes:\n{notes_text}\n\n"
        f"Recent conversation:\n{session.as_text()}\n\n"
        "Tools you may call:\n"
        f"{registry.descriptions()}\n\n"
        "Reply ONLY with JSON: {\"tool\": \"name\", \"arguments\": {...}} to call "
        "a tool, or {\"answer\": \"your spoken reply\"} when done."
    )


def _parse_json(text: str) -> dict | None:
    """Tolerantly extract the first JSON object from a model reply."""
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _llm_reply(
    registry: ToolRegistry, message: str, session: SessionMemory, store: NotesStore
) -> tuple[str | None, list[str]]:
    """One Gemini turn with a bounded (<=3) think -> act -> observe loop."""
    system = _system_prompt(registry, session, store)
    try:
        reply = llm.chat(system, message)
    except Exception:
        return None, []
    used: list[str] = []
    for _ in range(3):
        parsed = _parse_json(reply)
        if parsed is None:
            return reply, used  # free-form text is the final answer
        if "answer" in parsed:
            return str(parsed["answer"]), used
        if "tool" in parsed:
            name = str(parsed["tool"])
            args = parsed.get("arguments") or {}
            if not isinstance(args, dict):
                args = {}
            used.append(name)
            try:
                observation = registry.get(name)(**args)
            except Exception as exc:
                observation = f"tool error: {exc}"
            reply = llm.chat(
                system,
                f"Tool {name} returned:\n{observation}\n\n"
                'Now reply with your final JSON: {"answer": "your spoken reply"}.',
            )
    return None, []


def handle_message(
    message: str,
    session: SessionMemory,
    store: NotesStore,
    registry: ToolRegistry,
    force_mode: str | None = None,
) -> dict:
    """Process one user message and return the assistant's full response."""
    message = " ".join((message or "").split())
    mode = force_mode or ("llm" if llm.have_key() else "demo")
    intent = "conversation"
    tools_used: list[str] = []
    reply = ""

    if mode == "llm":
        reply, tools_used = _llm_reply(registry, message, session, store)
        if reply is None:
            mode = "demo"  # model failed: run the same pipeline with the demo brain

    if mode == "demo":
        brain = DemoBrain(registry)
        intent, reply, tools_used = brain.run(message)

    session.add(message, reply)
    return {"reply": reply, "intent": intent, "mode": mode, "tools_used": tools_used}
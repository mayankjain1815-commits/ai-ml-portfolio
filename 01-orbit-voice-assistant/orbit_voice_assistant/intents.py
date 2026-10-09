"""DemoBrain — the rule-based NLU that answers when no LLM key is set.

A tiny, classic NLP pipeline, implemented so an interviewer can trace it:

    1. collapse whitespace and lowercase the message;
    2. classify the *intent* with an ordered list of regex rules (first
       match wins — order is design, not accident);
    3. extract *slot values* (the arithmetic expression, the note text, the
       app name, the file name, the search query);
    4. dispatch to the matching tool and format a spoken-style reply.

Rule order is deliberate and tested:

    identity -> help -> time -> notes_add -> notes_delete -> notes_lookup
    -> open_app -> read_file -> web_search -> math -> greet -> fallback

So "what is your name" hits `identity` before math gets a chance, while
"hi, what is 2+2" still reaches `math`. Every rule is a named entry that
reports itself, which is what the introspected `intent` field in the API
response shows the frontend.
"""

from __future__ import annotations

import re
from typing import Callable

from .tools import ToolRegistry

BARE_MATH = re.compile(r"^[0-9+\-*/%^().\s]+$")


def _identity(_reg: ToolRegistry, _msg: str, _m) -> tuple[str, list[str]]:
    return (
        "I'm Orbit — a voice-first assistant built from scratch. Right now I'm "
        "running my deterministic demo brain: time, quick math, notes, bundled "
        "files, and app launching. Set a GEMINI_API_KEY and I switch to the "
        "Gemini model with the same tools.",
        [],
    )


def _help(_reg: ToolRegistry, _msg: str, _m) -> tuple[str, list[str]]:
    return (
        "I can tell the time, do quick math, remember notes, open allowlisted "
        "apps, read bundled files, and (online) search the web. Try: 'what time "
        "is it?', 'what is 8*7?', 'remember that Friday is the demo', "
        "'open calculator', 'read quick-tips', 'search for RAG pipelines'.",
        [],
    )


def _greet(_reg: ToolRegistry, _msg: str, _m) -> tuple[str, list[str]]:
    return (
        "Hello! I'm listening. Ask me the time, some quick math, or say "
        "'help' to see what I can do.",
        [],
    )


def _fallback(_reg: ToolRegistry, _msg: str, _m) -> tuple[str, list[str]]:
    return (
        "Hmm, I didn't quite catch that. Say 'help' to see what I can do.",
        [],
    )


def _time(reg: ToolRegistry, _msg: str, _m) -> tuple[str, list[str]]:
    return reg.get("current_time")(), ["current_time"]


def _math(reg: ToolRegistry, msg: str, m) -> tuple[str, list[str]]:
    expr = m.group(1) if m else msg
    return reg.get("calculator")(expression=expr), ["calculator"]


def _note_add(reg: ToolRegistry, _msg: str, m) -> tuple[str, list[str]]:
    text = m.group(1).strip().strip(".,;:!?")
    if not text:
        return "What should I save? Say it after 'remember' — for example, 'remember that Friday is the demo'.", []
    return reg.get("add_note")(text=text), ["add_note"]


def _note_delete(reg: ToolRegistry, _msg: str, m) -> tuple[str, list[str]]:
    key = m.group(1).strip() if m.group(1) else ""
    if not key:
        return "Tell me which note: an id, a #number, or a keyword.", []
    return reg.get("delete_note")(key=key), ["delete_note"]


def _note_lookup(reg: ToolRegistry, _msg: str, _m) -> tuple[str, list[str]]:
    return reg.get("list_notes")(), ["list_notes"]


def _open_app(reg: ToolRegistry, _msg: str, m) -> tuple[str, list[str]]:
    return reg.get("open_app")(name=m.group(1).strip()), ["open_app"]


def _read_file(reg: ToolRegistry, _msg: str, m) -> tuple[str, list[str]]:
    return reg.get("read_file")(name=m.group(1).strip()), ["read_file"]


def _web_search(reg: ToolRegistry, _msg: str, m) -> tuple[str, list[str]]:
    return reg.get("web_search")(query=m.group(1).strip()), ["web_search"]


class DemoBrain:
    """Intent classifier + slot filler + tool dispatcher, all deterministic."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry
        self.rules: list[tuple[str, re.Pattern | None, Callable | None]] = [
            ("identity", re.compile(r"\b(?:who are you|your name|what are you|about yourself)\b", re.I), _identity),
            ("help", re.compile(r"\b(?:what can you do|help|capabilities|what do you do)\b", re.I), _help),
            ("time", re.compile(r"\b(?:what time|what's the time|time|date|today's date|what day)\b", re.I), _time),
            ("notes_add", re.compile(r"\b(?:remember|save|note down|write down|jot down|note that)\b\s*(?:that|this)?\s*:?\s*(.+)$", re.I), _note_add),
            ("notes_delete", re.compile(r"\b(?:delete|remove|forget)\b\s*(?:the\s+)?(?:note\s+)?(.*)$", re.I), _note_delete),
            ("notes_lookup", re.compile(r"\b(?:my notes|show notes|list notes|read my notes|what did i (?:note|save|ask|say))\b", re.I), _note_lookup),
            ("open_app", re.compile(r"\bopen\b\s*(?:the\s+)?(?:app\s+)?([a-z][a-z ]*?)\s*$", re.I), _open_app),
            ("read_file", re.compile(r"\bread\b(?:\s+the)?(?:\s+file)?\s+([a-z0-9][\w .\-]*?)\s*$", re.I), _read_file),
            ("web_search", re.compile(r"\b(?:search|google|look up)\b\s*(?:for\s+)?(.+)$", re.I), _web_search),
            ("math", re.compile(r"(?:what is|what's|whats|how much is|calculate|compute|solve|evaluate)\s+([0-9+\-*/%^().\s]+)$", re.I), _math),
            ("greet", re.compile(r"\b(?:hi|hello|hey|good (?:morning|afternoon|evening))\b", re.I), _greet),
            ("fallback", None, _fallback),
        ]

    def run(self, message: str) -> tuple[str, str, list[str]]:
        """Classify, extract, dispatch. Returns (intent, reply, tools_used)."""
        msg = " ".join(message.split())
        # A bare arithmetic expression is math, even without a trigger word.
        if BARE_MATH.match(msg) and re.search(r"\d", msg):
            reply, used = _math(self.registry, msg, None)
            return "math", reply, used
        for intent, pattern, handler in self.rules:
            match = None
            if pattern is not None:
                match = pattern.search(msg)
                if match is None:
                    continue
            reply, used = handler(self.registry, msg, match)
            return intent, reply, used
        return "fallback", *_fallback(self.registry, msg, None)
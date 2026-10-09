"""Tools — the only way the assistant touches the outside world.

Every tool is a :class:`Tool`: a name, a description the LLM reads to decide
when to call it, and a plain function taking keyword arguments. The demo
brain calls them from its intent rules; the LLM brain calls the same registry
through the ReAct loop. One registry, two brains — that is the whole design.

Safety matters here because some tools are genuinely powerful:

* ``calculator`` parses with the ``ast`` module and whitelists node types —
  ``__import__('os')`` and friends fail at parse time, and exponent results
  are capped so nobody asks for a 300 MB integer.
* ``read_file`` only reads the bundled ``data/`` directory; path traversal
  (``..``, absolute paths) is rejected outright.
* ``open_app`` only launches applications on an explicit allowlist.
"""

from __future__ import annotations

import ast
import math
import operator as _op
import platform
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
APP_ALLOWLIST = {
    "notes": "Notes",
    "calculator": "Calculator",
    "calendar": "Calendar",
    "browser": "Safari",
    "safari": "Safari",
    "chrome": "Google Chrome",
    "mail": "Mail",
    "music": "Music",
    "photos": "Photos",
    "terminal": "Terminal",
    "finder": "Finder",
}
ALLOWED_OPS = {
    ast.Add: _op.add,
    ast.Sub: _op.sub,
    ast.Mult: _op.mul,
    ast.Div: _op.truediv,
    ast.Pow: _op.pow,
    ast.Mod: _op.mod,
    ast.USub: _op.neg,
    ast.UAdd: _op.pos,
}
MAX_RESULT = 1e12
MAX_EXPONENT = 1000


@dataclass
class Tool:
    name: str
    description: str
    fn: Callable[..., str]

    def __call__(self, **kwargs) -> str:
        return self.fn(**kwargs)


@dataclass
class ToolRegistry:
    tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        if tool.name in self.tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self.tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        return self.tools[name]

    def descriptions(self) -> str:
        return "\n".join(f"- {t.name}: {t.description}" for t in self.tools.values())


# ---------------------------------------------------------------------------
# Calculator (AST-whitelisted, so it is safe to evaluate user arithmetic)
# ---------------------------------------------------------------------------

def calculator(expression: str) -> str:
    """Evaluate a user-supplied arithmetic expression safely."""
    expr = expression.strip().lower()
    if not expr or not re.fullmatch(r"[0-9+\-*/%^().\s]+", expr):
        return "calculator: I can only handle numbers and + - * / % ^ ( )."
    try:
        value = _safe_eval(expr.replace("^", "**"))
    except (ValueError, ZeroDivisionError, SyntaxError, TypeError) as exc:
        return f"calculator: {exc}"
    if isinstance(value, float):
        value = round(value, 6)
    return f"{expr} = {value}"


def _safe_eval(expr: str) -> float:
    tree = ast.parse(expr, mode="eval")

    def _eval(node) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in ALLOWED_OPS:
            left, right = _eval(node.left), _eval(node.right)
            if isinstance(node.op, ast.Pow) and isinstance(right, (int, float)) and abs(right) > MAX_EXPONENT:
                raise ValueError("exponent too large")
            result = ALLOWED_OPS[type(node.op)](left, right)
            if not math.isfinite(result) or abs(result) > MAX_RESULT:
                raise ValueError("result is too large")
            return result
        if isinstance(node, ast.UnaryOp) and type(node.op) in ALLOWED_OPS:
            return ALLOWED_OPS[type(node.op)](_eval(node.operand))
        raise ValueError("only numbers and + - * / % ^ ( ) are allowed")

    return _eval(tree.body)


# ---------------------------------------------------------------------------
# Time, files, apps, search
# ---------------------------------------------------------------------------

def current_time() -> str:
    now = datetime.now()
    return f"It is {now:%H:%M} on {now:%A} {now.day} {now:%B} {now.year}."


def read_file(name: str) -> str:
    """Read one bundled data file by name (example: read_file(name='quick-tips'))."""
    safe = re.sub(r"[^a-z0-9_.-]", "", name.strip().lower())
    if not safe or ".." in safe or safe.startswith(("/", "\\")):
        return "read_file: that path is not allowed (traversal blocked)."
    # Accept with or without an extension, and with spaces as dashes.
    candidates = [DATA_DIR / safe, DATA_DIR / f"{safe}.md", DATA_DIR / f"{safe}.txt"]
    for path in candidates:
        if path.is_file():
            return f"--- {path.name} ---\n{path.read_text(encoding='utf-8')}"
    known = ", ".join(p.stem for p in sorted(DATA_DIR.glob("*")) if p.is_file())
    return f"read_file: no file named {safe!r}. Bundled files: {known or '(none)'}"


def open_app(name: str) -> str:
    """Launch an allowlisted macOS application by friendly name."""
    key = name.strip().lower()
    if key not in APP_ALLOWLIST:
        return (
            f"open_app: {name!r} is not on my allowlist. I can open: "
            + ", ".join(sorted(APP_ALLOWLIST))
        )
    app = APP_ALLOWLIST[key]
    if platform.system() != "Darwin":
        return f"open_app: launching apps is only wired up on macOS (would open {app})."
    try:
        subprocess.run(
            ["open", "-a", app], check=True, timeout=10,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return f"open_app: launching {app}."
    except Exception as exc:
        return f"open_app: could not launch {app}: {exc}"


def web_search(query: str) -> str:
    """Best-effort live search via DuckDuckGo Lite; never crashes offline."""
    try:
        import requests

        resp = requests.get(
            "https://lite.duckduckgo.com/lite/",
            params={"q": query},
            headers={"User-Agent": "orbit-demo/1.0"},
            timeout=6,
        )
        resp.raise_for_status()
        titles = [
            re.sub(r"<[^>]+>", "", m).strip()
            for m in re.findall(r'<a rel="nofollow"[^>]*>(.*?)</a>', resp.text)[:5]
        ]
        if titles:
            return "web_search results:\n" + "\n".join(f"- {t}" for t in titles)
    except Exception:
        pass
    return (
        "web_search: offline or blocked — demo mode can't reach the web. "
        "Try 'read quick-tips' to use my bundled notes instead."
    )


def add_note(text: str, store) -> str:
    note = store.add(text)
    return f"Saved note #{note['id']}: {note['text']}"


def list_notes(store) -> str:
    notes = store.list()
    if not notes:
        return "You have no notes yet."
    lines = [f"{i}. [{n['id']}] {n['text']}  ({n['created']})" for i, n in enumerate(notes, 1)]
    return "Your notes:\n" + "\n".join(lines)


def delete_note(key: str, store) -> str:
    return "Deleted that note." if store.delete(key) else (
        f"No note matched {key!r}. Say 'list my notes' to see them."
    )


def default_registry(store=None) -> ToolRegistry:
    """Build the registry, wiring the note tools to the given NotesStore.

    ``store`` is passed at call time (not import time) so tests can hand in a
    tmp_path-backed store and the LLM/demo brains share the same instance.

    Note: an empty ``NotesStore`` is falsy (it defines ``__len__``), so we
    must compare against ``None`` here — ``store or NotesStore()`` would
    silently throw away an empty-but-legitimate store.
    """
    from .memory import NotesStore

    store = store if store is not None else NotesStore()
    reg = ToolRegistry()
    for tool in (
        Tool("calculator", "Evaluate a user-supplied arithmetic expression. Arguments: expression (string).", calculator),
        Tool("current_time", "Return the current date and time.", current_time),
        Tool("add_note", "Save a short note to memory. Arguments: text (string).", lambda **kw: add_note(kw["text"], store)),
        Tool("list_notes", "List all saved notes.", lambda **_kw: list_notes(store)),
        Tool("delete_note", "Delete a note by id, #index, or keyword. Arguments: key (string).", lambda **kw: delete_note(kw["key"], store)),
        Tool("open_app", "Launch a macOS app. Arguments: name (string).", open_app),
        Tool("read_file", "Read a bundled data file. Arguments: name (string).", read_file),
        Tool("web_search", "Search the live web (best-effort). Arguments: query (string).", web_search),
    ):
        reg.register(tool)
    return reg
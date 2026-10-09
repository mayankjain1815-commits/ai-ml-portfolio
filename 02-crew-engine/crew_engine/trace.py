"""Trace — a lightweight audit log for every agent action.

One module-level :data:`trace` instance is shared by all agents in a crew, so
the final transcript reads like a play: which agent thought what, which
tools it called (with arguments), and what it produced. The transcript is
the "show your work" layer of the framework, and every CLI command prints
it with ``--trace``.

The singleton is intentionally simple: tests and callers ``reset()`` it when
they want a clean slate between runs.
"""

from __future__ import annotations

_TAG = {
    "agent": "AGENT",
    "tool": " TOOL",
    "warn": " WARN",
    "result": "RESULT",
    "decision": "DECIDE",
}


class Trace:
    def __init__(self) -> None:
        self._events: list[dict[str, str]] = []

    # -- recorders ---------------------------------------------------------
    def agent(self, name: str, detail: str) -> None:
        self._emit("agent", name, detail)

    def tool(self, name: str, tool_name: str, arguments: dict) -> None:
        self._emit("tool", name, f"{tool_name}({arguments})")

    def warn(self, name: str, detail: str) -> None:
        self._emit("warn", name, detail)

    def result(self, name: str, detail: str) -> None:
        self._emit("result", name, detail)

    def decision(self, name: str, detail: str) -> None:
        self._emit("decision", name, detail)

    # -- readout -----------------------------------------------------------
    def _emit(self, kind: str, name: str, detail: str) -> None:
        self._events.append({"kind": kind, "agent": name, "detail": detail})

    def events(self) -> list[dict[str, str]]:
        return list(self._events)

    def render(self) -> str:
        lines: list[str] = []
        for e in self._events:
            tag = _TAG.get(e["kind"], e["kind"].upper())
            lines.append(f"{tag} [{e['agent']}] {e['detail']}")
        return "\n".join(lines)

    def reset(self) -> None:
        self._events = []


# Shared singleton: every Agent in a crew logs to this one board-of-record.
trace = Trace()
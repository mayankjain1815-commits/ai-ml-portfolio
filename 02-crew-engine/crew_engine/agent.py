"""Agent — one specialist worker with a role, tools, and a brain.

An agent is the unit of reuse in a crew. It knows *who it is* (role, goal,
backstory — the text that shapes its behaviour), *what it can touch* (tools),
and *how it thinks* (strategy):

* ``"auto"`` -> real model via :mod:`crew_engine.llm` when a key is set,
  deterministic demo brain otherwise. This is the default: the same code is
  a live system with a key and an offline system without one.
* ``"llm"``  -> always try the model.
* ``"demo"`` -> always use the rule-based brain.

The demo brain dispatches on the task's ``kind`` (research / write / critique
/ plan / summarize / answer). The task says *what to do*; the persona text
only shapes *how it sounds*. That separation is what keeps the offline mode
deterministic and testable.
"""

from __future__ import annotations

import json
import re

from . import brain as demo
from .blackboard import Blackboard
from .task import Task
from .tools import ToolRegistry, load_corpus
from .trace import trace


class Agent:
    def __init__(
        self,
        name: str,
        role: str,
        goal: str,
        backstory: str = "",
        tools: ToolRegistry | None = None,
        strategy: str = "auto",
    ):
        self.name = name
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.tools = tools or ToolRegistry()
        self.strategy = strategy

    # -- public ------------------------------------------------------------
    def perform(self, task: Task, board: Blackboard) -> str:
        trace.agent(self.name, f"{self.role} — {task.title}")
        if self.strategy == "auto":
            from . import llm

            use_llm = llm.have_key()
        else:
            use_llm = self.strategy == "llm"

        if use_llm:
            output = self._think_llm(task, board)
            if output:
                return output
            trace.warn(self.name, "model path failed — falling back to demo brain")

        return self._think_demo(task, board)

    # -- LLM path ----------------------------------------------------------
    def _system_prompt(self, board: Blackboard) -> str:
        facts = "\n".join(f"- {f.content} [{f.source}]" for f in board.facts[:20])
        return (
            f"You are {self.name}, {self.role}.\n"
            f"Goal: {self.goal}\n"
            f"Backstory: {self.backstory or 'A focused specialist.'}\n\n"
            f"Available tools:\n{self.tools.descriptions()}\n\n"
            f"Blackboard facts so far:\n{facts or '- none yet'}\n\n"
            "If you need outside information, call a tool. Reply ONLY with a "
            'JSON object: {"tool": "name", "arguments": {...}} to call one '
            'tool, or {"answer": "your text result"} when done.'
        )

    def _think_llm(self, task: Task, board: Blackboard) -> str | None:
        from . import llm

        user = f"Task ({task.kind}): {task.title}\n\n{task.description}\n{task.context}"
        system = self._system_prompt(board)
        try:
            reply = llm.chat(system, user)
        except Exception as exc:
            trace.warn(self.name, f"LLM error: {exc}")
            return None

        for _ in range(3):  # bounded think -> act -> observe loop
            parsed = _parse_json(reply)
            if parsed is None:
                return reply  # raw text is the final answer
            if "answer" in parsed:
                return str(parsed["answer"])
            if "tool" in parsed:
                name = str(parsed["tool"])
                arguments = parsed.get("arguments") or {}
                if not isinstance(arguments, dict):
                    arguments = {}
                observation = self._use_tool(name, arguments)
                trace.tool(self.name, name, arguments)
                reply = llm.chat(
                    system,
                    f"Tool {name} returned:\n{observation}\n\n"
                    'Now reply with your final {"answer": ...}.',
                )
        return None

    def _use_tool(self, name: str, arguments: dict) -> str:
        try:
            tool = self.tools.get(name)
            return tool(**arguments)
        except Exception as exc:
            return f"tool error: {exc}"

    # -- demo path ---------------------------------------------------------
    def _think_demo(self, task: Task, board: Blackboard) -> str:
        topic = f"{task.title} {task.description}"
        kind = task.kind
        if kind == "research":
            output = demo.research(self.name, topic, board)
        elif kind == "write":
            facts = board.facts_for(topic)
            output = demo.write_draft(self.name, task.title, facts, _latest_feedback(board))
        elif kind == "critique":
            output = self._critique_demo(task, board)
        elif kind == "plan":
            output = self._plan_demo(task, board)
        elif kind == "summarize":
            facts = board.facts_for(topic)
            output = demo.generic_answer(self.name, topic, facts)
        else:  # 'answer'
            facts = board.facts_for(topic)
            output = demo.generic_answer(self.name, topic, facts)
        trace.result(self.name, output[:200])
        return output

    def _critique_demo(self, task: Task, board: Blackboard) -> str:
        draft = board.get_artifact("draft") or ""
        facts = board.facts_for(f"{task.title} {task.description}")
        scores, report = demo.critique(self.name, task.title, draft, facts)
        approved = "feedback: none — draft approved" in report
        board.put_artifact("_approved", "true" if approved else "false")
        round_i = str(board.artifacts.get("_round", "0"))
        board.put_artifact(f"_feedback_v{round_i}", report)
        return report

    def _plan_demo(self, task: Task, board: Blackboard) -> str:
        """Planner: assign one corpus document per worker, round-robin."""
        docs = sorted(load_corpus())
        if not docs:
            return "PLAN\n(no corpus documents available)"
        names = _worker_names(task.context)
        lines = ["PLAN"]
        for i, doc in enumerate(docs):
            worker = names[i % len(names)] if names else f"worker{i + 1}"
            lines.append(f"{worker} -> {doc}")
        return "\n".join(lines)


def _latest_feedback(board: Blackboard) -> str | None:
    """The most recent critic report on the board, or None."""
    keys = []
    for key in board.artifacts:
        if key.startswith("_feedback_v"):
            try:
                keys.append(int(key.split("_v")[1]))
            except ValueError:
                continue
    if not keys:
        return None
    return board.get_artifact(f"_feedback_v{max(keys)}")


def _worker_names(context: str) -> list[str]:
    marker = "Workers available:"
    if marker not in context:
        return []
    rest = context.split(marker, 1)[1]
    return [tok.strip() for tok in rest.replace(",", " ").split() if tok.strip()]


def _parse_json(text: str) -> dict | None:
    """Tolerantly extract a JSON object from a model reply."""
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
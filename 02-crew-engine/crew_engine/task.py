"""Task — one unit of work assigned to an agent."""

from __future__ import annotations

from dataclasses import dataclass

from .blackboard import Blackboard


@dataclass
class Task:
    title: str
    description: str                 # what to produce, in plain English
    agent: str | None = None         # assignee by name; None = crew decides
    context: str = ""                # extra guidance for the assignee
    expected_output: str = "text"    # 'text' | 'facts' | 'artifact'
    kind: str = "answer"             # research | write | critique | plan
                                     # | summarize | answer — the demo brain
                                     # dispatches on this, the LLM prompt
                                     # also names it so the model follows it

    def run(self, agent, board: Blackboard) -> str:
        """Execute this task against ``agent``, recording an audit trail."""
        board.say("SYSTEM", f"task assigned -> {agent.name}: {self.title}")
        result = agent.perform(self, board)
        board.say(agent.name, f"completed '{self.title}' ({len(result)} chars)")
        if self.expected_output == "artifact":
            board.put_artifact(self.title, result)
        if self.kind == "write":
            # Every writer publishes under the standard key, so any later
            # critic (in any pipeline) can find the draft to review.
            board.put_artifact("draft", result)
        return result
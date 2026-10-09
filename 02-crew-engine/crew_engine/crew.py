"""Crews — the orchestration patterns that combine agents into a system.

Three patterns ship with the framework, each mapping to a section of the
interview story:

* **SequentialCrew**   — agents take turns on ordered tasks (step 1 -> 2 -> 3).
* **SupervisorCrew**   — a planner splits the goal, workers execute one doc
                        each, the supervisor writes the final briefing.
* **ReflectiveCrew**   — writer -> critic -> revise, a bounded loop that stops
                        when the critic approves or the refinement budget
                        (``max_refinements``, default 2) is spent.

Every crew writes to its own :class:`Blackboard`, runs through the shared
:data:`~crew_engine.trace.trace` log, and returns a :class:`CrewResult` with
the output, the audit transcript, and how many rounds it took — the numbers
interviewers like ("the reflective loop converged in 2 rounds").
"""

from __future__ import annotations

from dataclasses import dataclass

from .agent import Agent
from .blackboard import Blackboard
from .task import Task
from .tools import load_corpus
from .trace import trace


@dataclass
class CrewResult:
    output: str
    transcript: str
    iterations: int = 0    # tasks executed
    refinements: int = 0   # only meaningful for ReflectiveCrew


class SequentialCrew:
    """One crew, ordered tasks, each assigned to an agent by name.

    Falls back to round-robin assignment when a task does not name an agent,
    so an LLM-produced task list still runs without a fix-up step.
    """

    def __init__(self, agents: list[Agent], tasks: list[Task]):
        self.agents = {a.name: a for a in agents}
        self.tasks = tasks
        self.board: Blackboard | None = None
        self.results: list[str] = []

    def run(self) -> CrewResult:
        board = Blackboard()
        self.board = board
        self.results = []
        roster = list(self.agents.values())
        for i, task in enumerate(self.tasks):
            agent = self.agents.get(task.agent) or roster[i % len(roster)]
            self.results.append(task.run(agent, board))
        output = self.results[-1] if self.results else ""
        return CrewResult(
            output=output,
            transcript=trace.render(),
            iterations=len(self.results),
        )


class SupervisorCrew:
    """Planner + workers: plan the goal, fan out, then summarize.

    The supervisor's plan task carries the worker roster in its ``context``
    so the demo planner can assign one corpus document per worker. In LLM
    mode the plan is whatever the model proposes; if it cannot be parsed into
    ``worker -> document`` assignments, the crew falls back to a deterministic
    round-robin so work still happens (never a half-run).
    """

    def __init__(
        self,
        supervisor: Agent,
        workers: list[Agent],
        max_iterations: int = 10,
    ):
        self.supervisor = supervisor
        self.workers = workers
        self.max_iterations = max_iterations
        self.board: Blackboard | None = None

    def run(self, goal: str = "Research a topic and brief the team") -> CrewResult:
        board = Blackboard()
        self.board = board
        roster = ", ".join(w.name for w in self.workers)

        plan_task = Task(
            title=f"Plan: {goal}",
            description=(
                "Split this goal into one subtask per worker, and assign "
                "each worker a single corpus document to research."
            ),
            agent=self.supervisor.name,
            context=f"Workers available: {roster}",
            kind="plan",
        )
        plan_text = plan_task.run(self.supervisor, board)

        executed = 0
        for subtask in self._plan_to_tasks(plan_text):
            if executed >= self.max_iterations:
                break
            worker = next((w for w in self.workers if w.name == subtask.agent), None)
            if worker is None:
                continue
            subtask.run(worker, board)
            executed += 1

        briefing_task = Task(
            title=f"Briefing: {goal}",
            description=f"Write a short briefing that summarizes the crew's findings on: {goal}",
            agent=self.supervisor.name,
            kind="summarize",
        )
        briefing = briefing_task.run(self.supervisor, board)

        return CrewResult(
            output=briefing,
            transcript=trace.render(),
            iterations=executed + 2,  # plan + briefing + worker research
        )

    def _plan_to_tasks(self, plan_text: str) -> list[Task]:
        """Parse ``worker -> document`` lines; round-robin as fallback."""
        assigns: list[tuple[str, str]] = []
        for line in plan_text.splitlines():
            line = line.strip()
            if "->" in line:
                worker, doc = (part.strip() for part in line.split("->", 1))
                assigns.append((worker, doc))
        if not assigns:
            docs = sorted(load_corpus())
            assigns = [
                (self.workers[i % len(self.workers)].name, doc)
                for i, doc in enumerate(docs)
            ]
        tasks: list[Task] = []
        for worker, doc in assigns:
            tasks.append(
                Task(
                    title=f"Research: {doc}",
                    description=(
                        f"Research the corpus document '{doc}' and record "
                        "its key facts on the blackboard, each with its source."
                    ),
                    agent=worker,
                    kind="research",
                )
            )
        return tasks


class ReflectiveCrew:
    """Generator -> critic -> revise, stopping on approval or budget.

    The loop is explicit and bounded: draft, score against the rubric, and
    either ship (approved) or revise. ``max_refinements`` (default 2) caps
    the loop so a stubborn critic can never spin forever — the "termination
    guarantee" interviewers look for.
    """

    def __init__(
        self,
        writer: Agent,
        critic: Agent,
        topic: str,
        max_refinements: int = 2,
    ):
        self.writer = writer
        self.critic = critic
        self.topic = topic
        self.max_refinements = max_refinements
        self.board: Blackboard | None = None

    def run(self) -> CrewResult:
        board = Blackboard()
        self.board = board

        research = Task(
            title=f"Research: {self.topic}",
            description=f"Gather grounded facts about: {self.topic}",
            agent=self.writer.name,
            kind="research",
        )
        research.run(self.writer, board)

        refinements = 0
        rounds = 0
        while True:
            board.put_artifact("_round", str(refinements))
            write_task = Task(
                title=f"Write report: {self.topic}",
                description=(
                    f"Produce a clear, structured, fully cited report titled '{self.topic}'."
                ),
                agent=self.writer.name,
                kind="write",
            )
            draft = write_task.run(self.writer, board)
            board.put_artifact("draft", draft)

            critique_task = Task(
                title=f"Review: {self.topic}",
                description=(
                    "Score the draft against the standard rubric and give "
                    "actionable feedback, or approve it."
                ),
                agent=self.critic.name,
                kind="critique",
            )
            critique_task.run(self.critic, board)
            rounds += 1

            approved = board.get_artifact("_approved") == "true"
            if approved or refinements >= self.max_refinements:
                break
            refinements += 1

        final = board.get_artifact("draft") or ""
        return CrewResult(
            output=final,
            transcript=trace.render(),
            iterations=rounds,       # draft+critique rounds
            refinements=refinements,  # revisions actually made
        )
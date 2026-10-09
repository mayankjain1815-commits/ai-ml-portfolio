"""Tests for the three crew orchestration patterns (offline demo mode)."""

from crew_engine.agent import Agent
from crew_engine.crew import ReflectiveCrew, SequentialCrew, SupervisorCrew
from crew_engine.task import Task
from crew_engine.tools import default_registry
from crew_engine.trace import trace


def _agents():
    reg = default_registry()
    researcher = Agent("Aria", "Researcher", "Find grounded facts.", tools=reg)
    writer = Agent("Bilal", "Writer", "Write clear reports.", tools=reg)
    critic = Agent("Cleo", "Critic", "Review drafts against the rubric.", tools=reg)
    supervisor = Agent("Sana", "Supervisor", "Plan, assign, brief.", tools=reg)
    workers = [
        Agent(n, "Researcher", "Research one document.", tools=reg)
        for n in ("Reza", "Mina", "Kai", "Tara")
    ]
    return researcher, writer, critic, supervisor, workers


# -- Sequential -------------------------------------------------------------

def test_sequential_runs_all_tasks_in_order():
    researcher, writer, critic, _, _ = _agents()
    crew = SequentialCrew(
        [researcher, writer, critic],
        [
            Task("Research: how AI began", "gather facts", agent="Aria", kind="research"),
            Task("Draft: how AI began", "write the report", agent="Bilal", kind="write"),
            Task("Review: how AI began", "review the draft", agent="Cleo", kind="critique"),
        ],
    )
    result = crew.run()
    assert result.iterations == 3
    assert len(crew.results) == 3
    assert result.output, "the review report is the crew's final output"
    assert crew.board is not None and len(crew.board.facts) >= 3
    assert crew.board.get_artifact("draft"), "the write step must publish a draft artifact"

    agent_names = [e["agent"] for e in trace.events() if e["kind"] == "agent"]
    assert agent_names == ["Aria", "Bilal", "Cleo"]


def test_sequential_falls_back_to_round_robin_assignment():
    researcher, writer, _, _, _ = _agents()
    crew = SequentialCrew(
        [researcher, writer],
        [
            Task("Research: t", "gather facts", agent="ghost", kind="research"),
            Task("Note: t", "plain answer", kind="answer"),
        ],
    )
    crew.run()
    agent_names = [e["agent"] for e in trace.events() if e["kind"] == "agent"]
    assert agent_names == ["Aria", "Bilal"]  # ghost -> Aria, unnamed -> Bilal


# -- Supervisor -------------------------------------------------------------

def test_supervisor_crew_plans_works_and_briefs():
    _, _, _, supervisor, workers = _agents()
    crew = SupervisorCrew(supervisor, workers, max_iterations=10)
    result = crew.run("Summarize the history of AI")
    assert result.iterations <= 10
    assert result.iterations >= 3  # plan + at least one worker + briefing
    assert result.output, "the briefing must be non-empty"
    assert crew.board is not None and len(crew.board.facts) >= 1


def test_supervisor_crew_respects_iteration_budget():
    _, _, _, supervisor, workers = _agents()
    crew = SupervisorCrew(supervisor, workers, max_iterations=1)
    result = crew.run("Summarize the history of AI")
    assert result.iterations == 3  # plan + exactly 1 worker + briefing
    assert result.output


def test_supervisor_plan_parses_worker_assignments():
    _, _, _, supervisor, workers = _agents()
    crew = SupervisorCrew(supervisor, workers)
    tasks = crew._plan_to_tasks(  # noqa: SLF001 - direct unit check
        "PLAN\nReza -> history-of-ai\nMina -> neural-networks"
    )
    assert [t.agent for t in tasks] == ["Reza", "Mina"]
    assert tasks[0].kind == "research"
    assert "history-of-ai" in tasks[0].title


def test_supervisor_plan_falls_back_to_round_robin():
    _, _, _, supervisor, workers = _agents()
    crew = SupervisorCrew(supervisor, workers)
    tasks = crew._plan_to_tasks(  # noqa: SLF001 - direct unit check
        "PLAN\n(unparseable LLM plan text)"
    )
    assert len(tasks) >= 1
    known = {w.name for w in workers}
    assert all(t.agent in known for t in tasks)


# -- Reflective -------------------------------------------------------------

def test_reflective_converges_with_a_revision():
    _, writer, critic, _, _ = _agents()
    crew = ReflectiveCrew(writer, critic, "How do neural networks work?", max_refinements=2)
    result = crew.run()
    assert result.refinements == 1, "one revision should satisfy the critic"
    assert result.iterations == 2
    assert "How it works" in result.output
    assert "## Key findings" in result.output
    assert crew.board.get_artifact("_approved") == "true"


def test_reflective_approves_without_revision_for_plain_topic():
    _, writer, critic, _, _ = _agents()
    crew = ReflectiveCrew(writer, critic, "The history of artificial intelligence", max_refinements=2)
    result = crew.run()
    assert result.refinements == 0
    assert result.iterations == 1
    assert "How it works" not in result.output
    assert crew.board.get_artifact("_approved") == "true"


def test_reflective_respects_zero_budget():
    _, writer, critic, _, _ = _agents()
    crew = ReflectiveCrew(writer, critic, "How do neural networks work?", max_refinements=0)
    result = crew.run()
    assert result.refinements == 0
    assert result.iterations == 1
    assert "How it works" not in result.output  # budget hit before revision
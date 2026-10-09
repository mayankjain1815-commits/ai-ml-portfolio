"""Command-line interface for Crew Engine.

Three subcommands, one per orchestration pattern:

    python -m crew_engine report "TOPIC"    # ReflectiveCrew: draft -> review -> revise
    python -m crew_engine supervise "GOAL"  # SupervisorCrew: plan -> workers -> briefing
    python -m crew_engine demo              # all three patterns on sample topics

Add ``--trace`` to any command to print the full audit log of every agent
action. With no API key every crew runs its deterministic demo brains — same
pipelines, zero network.
"""

from __future__ import annotations

import argparse
import sys

from .agent import Agent
from .crew import ReflectiveCrew, SequentialCrew, SupervisorCrew
from .task import Task
from .tools import default_registry
from .trace import trace

DEFAULT_TOPIC = "How do neural networks work?"
DEFAULT_GOAL = "Summarize the history of AI and the lessons it teaches"


def _divider(title: str) -> str:
    return f"\n{'=' * 68}\n{title}\n{'=' * 68}"


def _demo_banner() -> None:
    from . import llm

    if not llm.have_key():
        print(f"\n{llm.demo_note()}")


def _make_crew() -> tuple[list[Agent], Agent, list[Agent]]:
    """One researcher/writer/critic trio + a supervisor team (demo-friendly)."""
    registry = default_registry()
    researcher = Agent(
        "Aria", "Researcher",
        "Find grounded facts in the corpus and post them to the blackboard, each with its source.",
        tools=registry,
    )
    writer = Agent(
        "Bilal", "Writer",
        "Assemble blackboard facts into a clear, structured, fully cited report.",
        tools=registry,
    )
    critic = Agent(
        "Cleo", "Critic",
        "Score drafts against the four-axis rubric, demand citations, and ask for a 'How it works' section when the topic is about a mechanism.",
        tools=registry,
    )
    supervisor = Agent(
        "Sana", "Supervisor",
        "Plan the work, assign one document per worker, and write the final briefing.",
        tools=registry,
    )
    workers = [
        Agent(name, "Researcher",
              "Research the assigned corpus document and record its key facts.",
              tools=registry)
        for name in ("Reza", "Mina", "Kai", "Tara")
    ]
    return [researcher, writer, critic], supervisor, workers


def cmd_report(args: argparse.Namespace) -> int:
    trio, _, _ = _make_crew()
    writer, critic = trio[1], trio[2]
    crew = ReflectiveCrew(writer, critic, args.topic, max_refinements=args.refinements)
    result = crew.run()
    print(_divider(f"Reflective crew — {args.topic}"))
    print(result.output)
    print(f"\nrefinements: {result.refinements} | draft+review rounds: {result.iterations}")
    if args.trace:
        print(_divider("Audit log"))
        print(result.transcript)
    return 0


def cmd_supervise(args: argparse.Namespace) -> int:
    _, supervisor, workers = _make_crew()
    crew = SupervisorCrew(supervisor, workers, max_iterations=args.max_iterations)
    result = crew.run(args.goal)
    print(_divider(f"Supervisor crew — {args.goal}"))
    print(result.output)
    print(f"\ntasks executed: {result.iterations}")
    if args.trace:
        print(_divider("Audit log"))
        print(result.transcript)
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    trio, supervisor, workers = _make_crew()
    researcher, writer, critic = trio
    topic = args.topic or DEFAULT_TOPIC
    goal = args.goal or DEFAULT_GOAL
    _demo_banner()

    # 1. Sequential pipeline -------------------------------------------------
    sequential = SequentialCrew(
        [researcher, writer, critic],
        [
            Task(f"Research: {topic}", f"Gather grounded facts about: {topic}",
                 agent=researcher.name, kind="research"),
            Task(f"Draft: {topic}", f"Write a structured report titled '{topic}'.",
                 agent=writer.name, kind="write"),
            Task(f"Review: {topic}", "Review the draft against the standard rubric.",
                 agent=critic.name, kind="critique"),
        ],
    )
    seq_result = sequential.run()
    seq_result = sequential.run()
    print(_divider("1. Sequential pipeline (research -> draft -> review)"))
    print("Research notes:")
    print(sequential.results[0])
    print("\nDraft:")
    print(sequential.results[1])
    print("\nReview:")
    print(sequential.results[2])

    # 2. Supervisor crew ------------------------------------------------------
    supervised = SupervisorCrew(supervisor, workers, max_iterations=args.max_iterations)
    sup_result = supervised.run(goal)
    print(_divider("2. Supervisor crew (plan -> workers -> briefing)"))
    print(sup_result.output)
    print(f"\ntasks executed: {sup_result.iterations}")

    # 3. Reflective crew ------------------------------------------------------
    reflective = ReflectiveCrew(writer, critic, topic, max_refinements=args.refinements)
    ref_result = reflective.run()
    print(_divider("3. Reflective crew (draft -> critic -> revise)"))
    print(ref_result.output)
    print(f"\nrefinements: {ref_result.refinements} | draft+review rounds: {ref_result.iterations}")

    if args.trace:
        print(_divider("Combined audit log"))
        print(ref_result.transcript)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crew_engine",
        description="A from-scratch multi-agent framework: sequential, supervisor, "
                    "and reflective crews that run offline or with Gemini.",
    )
    # --trace is shared by every subcommand, so it lives in a parent parser.
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--trace", action="store_true",
                        help="print the full audit log of every agent action")
    sub = parser.add_subparsers(dest="command", required=True)

    p_report = sub.add_parser("report", parents=[parent],
                              help="ReflectiveCrew: draft, review, revise")
    p_report.add_argument("topic", nargs="?", default=DEFAULT_TOPIC)
    p_report.add_argument("--refinements", type=int, default=2,
                          help="max revision rounds (default 2)")
    p_report.set_defaults(fn=cmd_report)

    p_supervise = sub.add_parser("supervise", parents=[parent],
                                 help="SupervisorCrew: plan, work, brief")
    p_supervise.add_argument("goal", nargs="?", default=DEFAULT_GOAL)
    p_supervise.add_argument("--max-iterations", type=int, default=10,
                             help="cap on subtasks executed (default 10)")
    p_supervise.set_defaults(fn=cmd_supervise)

    p_demo = sub.add_parser("demo", parents=[parent],
                            help="run all three crew patterns on sample topics")
    p_demo.add_argument("--topic", default=None)
    p_demo.add_argument("--goal", default=None)
    p_demo.add_argument("--refinements", type=int, default=2)
    p_demo.add_argument("--max-iterations", type=int, default=10)
    p_demo.set_defaults(fn=cmd_demo)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    trace.reset()  # one clean audit log per invocation
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
"""Command-line interface for Skill Forge.

Subcommands mirror the skill lifecycle:

    list     see what skills exist
    search   rank skills for a query (no skill is executed)
    pick     choose exactly one skill for a task, with reasoning
    pack     show the bounded prompt that would be sent to a model
    run      execute a skill with inputs
    show     print a skill's SKILL.md
    install  copy a skill folder into the local library
    demo     one scripted end-to-end run (start here)
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import llm
from .loader import DEFAULT_INSTALL_DIR, discover, load_library
from .packer import DEFAULT_BUDGET, pack
from .runner import parse_inputs, run
from .selector import KeywordSelector, LLMSelector
from .skill import SkillParseError

BAR = "-" * 62


def _library(args) -> tuple:
    install = Path(args.skills_dir) if args.skills_dir else None
    lib = load_library(install_dir=install)
    return lib, install


def _make_selector(lib, use_llm: bool):
    skills = lib.all()
    keyword = KeywordSelector(skills)
    return LLMSelector(skills, fallback=keyword) if use_llm else keyword


def cmd_list(args) -> int:
    lib, _ = _library(args)
    print(f"{len(lib)} skills loaded" + (f" ({', '.join(lib.overrides)} overridden)" if lib.overrides else ""))
    print(BAR)
    print(f"{'NAME':<20} {'MODE':<8} {'RISK':<9} DESCRIPTION")
    print(BAR)
    for s in lib.all():
        print(f"{s.name:<20} {s.mode:<8} {s.risk:<9} {s.description}")
    return 0


def cmd_search(args) -> int:
    lib, _ = _library(args)
    selector = KeywordSelector(lib.all())
    scored = sorted(
        ((s, selector.score(args.query, s)) for s in lib.all()),
        key=lambda p: (-p[1], p[0].name),
    )
    print(f"Ranking for: {args.query!r}\n")
    for skill, score in scored:
        bar = "#" * int(score)
        print(f"  {score:>4.0f}  {skill.name:<20} {bar}")
    top, top_score = scored[0]
    if top_score == 0:
        print("\nNo skill matched. Try `list` to see what's available.")
    else:
        print(f"\nBest match: {top.name} — run `pick {args.query!r}` for reasoning.")
    return 0


def cmd_pick(args) -> int:
    lib, _ = _library(args)
    selector = _make_selector(lib, use_llm=not args.offline and llm.have_key())
    sel = selector.select(args.task)
    print(f"Task   : {args.task}")
    print(f"Skill  : {sel.skill.name}")
    print(f"Mode   : {sel.skill.mode}  |  risk: {sel.skill.risk}")
    print(f"Strategy: {sel.strategy}  |  confidence: {sel.confidence}")
    if sel.alternatives:
        runner_up = ", ".join(f"{n} ({s:.0f})" for n, s in sel.alternatives)
        print(f"Next   : {runner_up}")
    print(f"\nWhy    : triggers {list(sel.skill.triggers)} matched the task wording.")
    return 0


def cmd_pack(args) -> int:
    lib, _ = _library(args)
    selector = _make_selector(lib, use_llm=not args.offline and llm.have_key())
    skill = lib.get(args.skill) if args.skill else selector.select(args.task).skill
    task = args.task or f"Run the {skill.name} skill."
    try:
        packed = pack(skill, task, budget=args.budget)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"Packed prompt for skill '{skill.name}'")
    print(f"tokens: {packed.tokens}/{packed.budget} "
          f"({packed.utilisation:.0%} of budget, "
          f"{packed.truncated_lines} lines truncated)")
    print(BAR)
    print(packed.text)
    return 0


def cmd_run(args) -> int:
    lib, _ = _library(args)
    try:
        skill = lib.get(args.skill)
        inputs = parse_inputs(args.input or [])
    except (KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    result = run(skill, inputs, task=args.task)
    label = {"action": "action (deterministic)", "llm": "model-executed",
             "plan": "execution plan (demo mode)"}[result.mode]
    print(f"skill : {result.skill}")
    print(f"via   : {label}")
    print(BAR)
    print(result.output)
    return 0 if result.ok else 1


def cmd_show(args) -> int:
    lib, _ = _library(args)
    try:
        skill = lib.get(args.skill)
    except KeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    origin = skill.path.parent.name if skill.path else "?"
    print(f"# {skill.name}  (mode={skill.mode}, risk={skill.risk}, folder={origin})")
    print(f"# {skill.description}\n")
    print(skill.body)
    return 0


def cmd_install(args) -> int:
    src = Path(args.path).expanduser().resolve()
    if not (src / "SKILL.md").exists():
        print(f"error: {src} does not contain a SKILL.md", file=sys.stderr)
        return 2
    try:
        # Validate before copying — never install something we can't parse.
        from .skill import load_skill

        skill = load_skill(src)
    except SkillParseError as exc:
        print(f"error: invalid skill: {exc}", file=sys.stderr)
        return 2

    target_root = Path(args.target).expanduser().resolve() if args.target else DEFAULT_INSTALL_DIR
    dest = target_root / skill.name
    if dest.exists() and not args.force:
        print(f"error: {dest} already exists (use --force to replace)", file=sys.stderr)
        return 2
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    print(f"installed '{skill.name}' -> {dest}")
    print("It now overrides the built-in version of the same name (if any).")
    return 0


def cmd_demo(args) -> int:
    """Scripted end-to-end run — the command the README quick-start uses."""
    lib, _ = _library(args)
    print(BAR)
    print("SKILL FORGE — end-to-end demo" + ("" if llm.have_key() else " (demo mode, no API key)"))
    if not llm.have_key():
        print(llm.demo_note())
    print(BAR)

    tasks = [
        ("analyze the csv in data/sample.csv and tell me total revenue", None),
        ("convert 12.5 km to miles", {"value": "12.5", "from_unit": "km", "to_unit": "miles"}),
    ]
    for task, direct_inputs in tasks:
        print(f"\n> {task}")
        selector = KeywordSelector(lib.all())
        sel = selector.select(task)
        print(f"  picked: {sel.skill.name}  [{sel.strategy}, confidence {sel.confidence}]")

        inputs = direct_inputs or _demo_inputs(sel.skill)
        result = run(sel.skill, inputs, task=task)
        print(f"  ran via: {result.mode}")
        print("  " + "-" * 58)
        for line in result.output.splitlines()[:14]:
            print(f"  {line}")
        if len(result.output.splitlines()) > 14:
            print(f"  ... ({len(result.output.splitlines()) - 14} more lines)")

    print(f"\nNext: `pick \"your task\"`, `pack --task \"...\"`, `list` for everything.")
    return 0


def _demo_inputs(skill) -> dict[str, str]:
    sample_csv = Path(__file__).resolve().parent.parent / "data" / "sample.csv"
    default = {
        "csv-analyzer": {"path": str(sample_csv)},
        "summarize-text": {"text": (
            "The James Webb Space Telescope is the largest optical telescope in space. "
            "Its high resolution and sensitivity allow it to view objects too far away "
            "for the Hubble Space Telescope. Webb observes in the infrared, while Hubble "
            "primarily observes in ultraviolet and visible light. Together they give "
            "astronomers a much fuller picture of the universe."
        )},
    }
    return default.get(skill.name, {})


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="skill-forge",
        description="Discover, select, pack and run agent skills.",
    )
    p.add_argument(
        "--skills-dir",
        help="alternate directory to load skills from (default: built-in + ./.agents/skills)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list all available skills").set_defaults(fn=cmd_list)

    sp = sub.add_parser("search", help="rank skills for a free-text query")
    sp.add_argument("query")
    sp.set_defaults(fn=cmd_search)

    sp = sub.add_parser("pick", help="choose one skill for a task, with reasoning")
    sp.add_argument("task")
    sp.add_argument("--offline", action="store_true", help="force the keyword selector")
    sp.set_defaults(fn=cmd_pick)

    sp = sub.add_parser("pack", help="show the bounded prompt for a task/skill")
    sp.add_argument("--task", help="task description (used when --skill omitted)")
    sp.add_argument("--skill", help="pack this skill directly instead of selecting")
    sp.add_argument("--budget", type=int, default=DEFAULT_BUDGET, help="token budget")
    sp.add_argument("--offline", action="store_true", help="force the keyword selector")
    sp.set_defaults(fn=cmd_pack)

    sp = sub.add_parser("run", help="execute a skill with inputs")
    sp.add_argument("skill")
    sp.add_argument("--input", action="append", metavar="KEY=VALUE",
                    help="repeatable input, e.g. --input value=12.5")
    sp.add_argument("--task", help="task text (used by guided skills in model mode)")
    sp.set_defaults(fn=cmd_run)

    sp = sub.add_parser("show", help="print a skill's SKILL.md")
    sp.add_argument("skill")
    sp.set_defaults(fn=cmd_show)

    sp = sub.add_parser("install", help="install a skill folder into the local library")
    sp.add_argument("path", help="folder containing SKILL.md")
    sp.add_argument("--target", help=f"install directory (default: {DEFAULT_INSTALL_DIR})")
    sp.add_argument("--force", action="store_true", help="replace an existing skill")
    sp.set_defaults(fn=cmd_install)

    sub.add_parser("demo", help="scripted end-to-end run").set_defaults(fn=cmd_demo)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except SkillParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130

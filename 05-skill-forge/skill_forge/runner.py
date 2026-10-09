"""Skill execution — run a skill against concrete inputs.

Two execution paths, chosen by the skill's ``mode`` frontmatter:

* ``action``   — the skill ships an ``action.py`` exposing
  ``run(inputs: dict) -> str``. Fully deterministic, works offline, and is
  what makes skills *do* things instead of just *advise*. This is the
  "compiled" path.

* ``guided``   — the SKILL.md body is a playbook for a model. With a key,
  the packed prompt goes to the LLM. Without one, we print the execution
  plan (the steps, the inputs, what a model *would* do) — honest about what
  happened rather than pretending an answer exists.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from dataclasses import dataclass

from . import llm
from .packer import pack
from .skill import Skill


@dataclass(frozen=True)
class RunResult:
    skill: str
    mode: str  # "action" | "llm" | "plan"
    output: str
    ok: bool


def _load_action(skill: Skill):
    """Import ``action.py`` from the skill's folder by path.

    Loading by path (not package import) means users can install arbitrary
    skill folders — including third-party ones — without them needing to be
    inside our Python package.
    """
    action_path = skill.folder / "action.py" if skill.folder else None
    if not action_path or not action_path.exists():
        return None
    mod_name = f"skill_forge_action_{skill.name.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(mod_name, action_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return getattr(module, "run", None)


def parse_inputs(pairs: list[str]) -> dict[str, str]:
    """``["hours=2", "topic=sorting"]`` -> dict. Clear error on no ``=``."""
    inputs: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(
                f"Input {pair!r} must look like key=value (e.g. hours=2)"
            )
        key, _, value = pair.partition("=")
        inputs[key.strip()] = value.strip()
    return inputs


def run(skill: Skill, inputs: dict[str, str], *, task: str | None = None) -> RunResult:
    """Execute ``skill`` with ``inputs``; never raises for skill-level
    failures — errors are returned in the result so the CLI can print them
    without a traceback wall."""

    # 1) Compiled path: deterministic action shipped with the skill.
    if skill.mode == "action" or skill.has_action:
        action = _load_action(skill)
        if action is not None:
            try:
                output = action(inputs)
                return RunResult(skill.name, "action", str(output).rstrip(), True)
            except Exception as exc:
                return RunResult(
                    skill.name,
                    "action",
                    f"Action failed: {exc}",
                    False,
                )

    # 2) Guided path with a real model.
    if llm.have_key():
        packed = pack(skill, task or _describe_task(skill, inputs), budget=1600)
        try:
            output = llm.complete(packed.text, system=None)
            return RunResult(skill.name, "llm", output.strip(), True)
        except Exception as exc:
            return RunResult(skill.name, "llm", f"Model call failed: {exc}", False)

    # 3) Honest offline fallback: show the plan, not a fake answer.
    return RunResult(skill.name, "plan", _plan(skill, inputs), True)


def _describe_task(skill: Skill, inputs: dict[str, str]) -> str:
    if not inputs:
        return f"Run the {skill.name} skill."
    joined = ", ".join(f"{k}={v}" for k, v in inputs.items())
    return f"Run the {skill.name} skill with inputs: {joined}."


def _plan(skill: Skill, inputs: dict[str, str]) -> str:
    """Offline output for guided skills: the execution plan."""
    lines = [f"PLAN — skill: {skill.name} (guided, demo mode)"]
    if inputs:
        lines.append("Inputs:")
        lines.extend(f"  {k}: {v}" for k, v in inputs.items())
    lines.append("Steps the model would execute:")
    step = 1
    numbered = re.compile(r"\d+\.")
    for raw in skill.body.splitlines():
        stripped = raw.strip()
        is_bullet = stripped.startswith(("- ", "* "))
        is_numbered = bool(numbered.match(stripped.split(" ", 1)[0]))
        if is_bullet or is_numbered:
            lines.append(f"  {step}. {stripped.lstrip('-* ').strip()}")
            step += 1
    lines.append(
        "(Set GEMINI_API_KEY to execute this skill with a real model.)"
    )
    return "\n".join(lines)

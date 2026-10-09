# 05. Skill Forge

> A from-scratch agent skills system: discover, select, pack, and run `SKILL.md` playbooks.

**Inspired by:** [agentic-awesome-skills](https://github.com/sickn33/agentic-awesome-skills) (a 2,600+ skill library for coding agents) and the [agent skills](https://github.com/Shubhamsaboo/awesome-llm-apps/tree/main/agent_skills) section of awesome-llm-apps.

## What it does

- **`list`** — shows every installed skill: name, mode (action/guided), risk level, description.
- **`search` / `pick`** — ranks skills for a task written in plain English, with *why* it picked the winner.
- **`pack`** — builds the exact prompt that would be sent to a model and shows its token budget. This is the project's "aha" feature: it makes context-window management visible.
- **`run`** — executes a skill. Six skills ship real executable code (`action.py`); three are model-guided playbooks.
- **`install`** — drops any skill folder into your local library; installed skills upgrade their built-in namesakes.
- Ships **9 skills** out of the box: `csv-analyzer`, `summarize-text`, `unit-convert`, `study-plan`, `budget-calculator`, `flashcards` (executable) plus `regex-builder`, `git-commit-message`, `debug-helper` (model-guided).

## Quick start

```bash
cd 05-skill-forge
python3 -m venv .venv && source .venv/bin/activate   # or use the repo-root venv
pip install -r requirements.txt

python -m skill_forge demo          # scripted end-to-end run — no API key needed
python -m skill_forge list          # see everything available
python -m skill_forge pick "analyze a csv for me"
python -m skill_forge run csv-analyzer --input path=data/sample.csv
python -m skill_forge pack --task "convert 12.5 km to miles" --budget 600
```

## How it works

```
 ┌─────────────┐   ┌──────────────┐   ┌────────────┐   ┌─────────────┐
 │ your task   │──▶│  selector    │──▶│  packer    │──▶│  runner     │
 │ "analyze..."│   │ keyword / LLM│   │ token-budget│  │ action / LLM│
 └─────────────┘   └──────────────┘   └────────────┘   └─────────────┘
        │                │                  │                │
        │          scores every skill     bounds the        executes the
        │          by trigger overlap     prompt to fit     skill or shows
        │          (or asks the model)    the context       the plan
        ▼                ▼                  ▼                ▼
   SKILL.md library    choice + reasons   packed prompt    output / result
```

1. You type a task: `convert 12.5 km to miles`.
2. The **selector** scores every skill. Trigger words (`convert`, `km`, `miles`) hit `unit-convert` hard — it wins. In demo mode this is a deterministic keyword scorer; with a `GEMINI_API_KEY` the model picks from the same roster (name + description only).
3. The **packer** builds a system prompt containing the *chosen skill's* full instructions and nothing else, and guarantees it fits a token budget — trimming whole lines if a skill body is too long, and telling you exactly how much it dropped.
4. The **runner** executes: executable skills call their `action.py` (deterministic, offline, exact), guided skills go to the model, or — with no key — print an honest execution plan.

## Demo mode vs. real mode

| | No API key (demo) | With `GEMINI_API_KEY` |
|---|---|---|
| Skill selection | keyword scorer with confidence + runners-up | model picks from the same roster |
| Executable skills (`csv-analyzer`, `unit-convert`, ...) | real `action.py` runs — exact, deterministic | same actions (no model needed) |
| Guided skills (`regex-builder`, `debug-helper`, ...) | prints the execution plan the model would follow | model executes the pack instructions |
| `pack` | identical — packing is pure logic | identical |

Copy `.env.example` to `.env` and add your key. Everything in demo mode is *real* — never a stub.

## Project structure

```
05-skill-forge/
├── skill_forge/          # the Python package
│   ├── skill.py          # SKILL.md parser (frontmatter + body)
│   ├── loader.py         # discovery: built-in skills + .agents/skills
│   ├── selector.py       # KeywordSelector + LLMSelector
│   ├── packer.py         # token-budget prompt packing
│   ├── runner.py         # executes skills via action.py / LLM / plan
│   ├── llm.py            # Gemini REST client with demo fallback
│   └── cli.py            # list / search / pick / pack / run / show / install / demo
├── skills/               # 9 shipped skills, each a folder with SKILL.md
│   └── <name>/SKILL.md   #   (action skills also ship action.py)
├── data/sample.csv       # demo data with planted quality issues
└── tests/                # 57 tests: parser, selector, packer, runner, CLI
```

## Explain it like I'm 19

Think of an AI agent as a body with a backpack. The backpack can hold
*game manuals* (skills). If you cram all 20 manuals in, your arms are so full
you can barely move — that's a huge system prompt: expensive, slow, and full
of irrelevant noise. Skill Forge is the organizer: it looks at the level you're
on, pulls out *one* manual, reads you the relevant page, and puts the rest
back. Same knowledge, far less baggage, and every page is checked to fit the
bag before you leave.

## Explain it in an interview

**Q: Why not just put all your skill instructions in the system prompt?**
A: Token cost and attention. Every token in the prompt is paid for on every
call, and models focus best on a small, relevant context. Packing only the
chosen skill keeps costs down and precision up — and `pack` makes the trade
measurable, so you can see a 3× budget difference between loading all skills
vs one.

**Q: How does skill selection work without a model?**
A: The keyword scorer is a small weighted ranking: +3 per trigger-word hit,
+2 for name overlap, +1 for description overlap, on word boundaries. It's
deliberately simple — easy to debug, easy to explain, and good enough that
demo mode is genuinely useful rather than a placeholder.

**Q: What's the difference between an "action" and a "guided" skill?**
A: Actions are compiled: a `run(inputs)` function that executes the logic
deterministically — exact, testable, offline. Guided skills are playbooks:
instructions a model follows. The inspired insight is splitting the fast
deterministic path from the slow reasoning path, like a CPU's built-in
instructions vs interpreted code.

**Q: How do you keep a skill from breaking the context budget?**
A: The packer measures the full assembled prompt (header + skill body + task +
truncation notice) against a budget using a ~4-characters-per-token estimate,
and trims whole lines from the body's tail until it fits. If even the header
and task exceed the budget, it raises a clear error instead of silently
sending garbage.

**Q: What would you add for production?**
A: Skill versioning plus a test harness per skill (the upstream AAS repo runs
a CI eval gate per skill), risk-gating risky skills behind confirmation, and
telemetry on which skills users actually invoke — that tells you what to
curate next.

## Ideas to extend it

- Add a `--json` flag to the CLI so skills can be driven by scripts.
- Build a `curl`-style MCP server exposing skills to other tools.
- Add per-skill evals, like AAS's security + eval CI gate.
- Implement pagination when multiple skills are needed for one task.
- Write your own skill folder and `install` it — try a `meal-planner`.

## Tests

```bash
cd 05-skill-forge
../.venv/bin/python -m pytest -q     # 57 tests, fully offline
```

Covers: SKILL.md parsing edge cases, selector ranking and word boundaries,
the packer's exact-fit guarantee, and every CLI subcommand end-to-end.
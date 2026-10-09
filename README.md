# AI/ML Project Portfolio

> Six self-contained AI/ML projects — complex enough to impress, simple enough to explain out loud in two minutes. Every project runs **fully offline in demo mode** and upgrades to real LLM calls the moment a `GEMINI_API_KEY` is set.

Built from scratch (no langchain, no streamlit, no SDK wrappers) so every design decision is mine to explain and defend — the mechanics are the point.

## The projects

| # | Project | What it is | Demo command |
|---|---------|------------|--------------|
| 01 | **Orbit Voice Assistant** | Voice-first browser assistant: Web Speech API frontend, rule-based NLU (intent → slots → tools), AST-safe calculator, persistent notes, app allowlist. ReAct tool loop over the same tools in LLM mode. Flask, port **5101**. | `python -m orbit_voice_assistant` |
| 02 | **Crew Engine** | A multi-agent framework from scratch: sequential, supervisor, and reflective crews sharing a blackboard (cited facts + artifacts + audit trace). Deterministic demo brains; JSON tool-calling loop with Gemini. 4-doc corpus included. | `python -m crew_engine demo --trace` |
| 03 | **RAG Studio** | Retrieval-augmented generation, hand-built: chunking, TF-IDF index, retrieval, generation, and an eval harness (recall@k, MRR, faithfulness). | `python -m rag_studio demo` |
| 04 | **Model Watch** | MLOps monitoring: population-stability-index and KS drift detection by hand, sliding-window alerts, model registry, training + simulation + dashboard (Flask, port **5104**) + CLI reports. | `python -m model_watch demo` |
| 05 | **Skill Forge** | An agent skill system: SKILL.md format, YAML-era parsing, selectors (exact/phrase/keyword), token-budget packing, and a CLI to create/verify/serve skills. 9 bundled skills, 57 tests. | `python -m skill_forge demo` |
| 06 | **GH Activity Forge** | GitHub contribution-graph generator: seeded activity profiles (Poisson/streaks/vacations), a hand-built SVG renderer with GitHub's exact palette, report bundle, and an *opt-in, loudly-warned* fake-commit script emitter. | `python -m gh_activity_forge --year 2026` |

## The one idea that unifies them

**Demo mode is a parallel implementation, not a stub.** Every project ships a deterministic, rule-based brain that performs the *same pipeline* the LLM performs — real extraction, real rubric scoring, real retriever math — so the whole portfolio runs offline, in CI, and in a live demo with zero keys. Set a `GEMINI_API_KEY` in any project's `.env` and the same code upgrades to real model calls with an honest fallback. Ask any project what it would do with a key and the answer is architectural, not aspirational.

## Repo layout

```
.
├── 01-orbit-voice-assistant/   Flask app + Web Speech frontend (port 5101)
├── 02-crew-engine/             multi-agent crews on a blackboard
├── 03-rag-studio/              RAG pipeline + eval harness
├── 04-model-watch/             drift detection + model registry (port 5104)
├── 05-skill-forge/             agent skill system
├── 06-gh-activity-forge/       contribution-graph generator
├── docs/
│   ├── BUILD_SPEC.md           shared conventions every project follows
│   └── LEARNING_GUIDE.md       interview prep: Q&A per project
├── .venv/                      shared Python 3.13 environment (gitignored)
└── README.md                   you are here
```

Each project is self-contained: its own `README.md`, `requirements.txt`, `.env.example`, `.gitignore`, and `tests/` — no imports across projects. Run everything from the repo's venv:

```bash
# one venv for the whole portfolio
python3.13 -m venv .venv && .venv/bin/pip install -r <project>/requirements.txt

# tests for every project (all offline)
cd 01-orbit-voice-assistant && ../.venv/bin/python -m pytest -q

# a live demo of every project (no API key needed)
cd 02-crew-engine && ../.venv/bin/python -m crew_engine demo --trace
```

## Interview framing

This portfolio is built to hold up in a technical interview. For every project: *what's the 2-minute story, which part was hardest, and where's the code that proves it.* The [learning guide](docs/LEARNING_GUIDE.md) contains the Q&A I rehearsed for each project, along with the follow-ups an interviewer is likely to ask.

## License & credit

Learning portfolio. All code, corpus articles, and data files are original or freely licensed (see each project's README). Inspired-by sources are credited per project — the point of a rebuild is that you understand what you ship.
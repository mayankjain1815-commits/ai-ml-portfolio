# BUILD SPEC — shared conventions for every project in this repo

This repo contains six self-contained projects. They must all feel like they were
built by the same person: consistent structure, consistent voice, consistent quality.

**Audience:** a 19–20 year old student (and interviewers). Every project must be
*complex enough to be impressive, simple enough to explain out loud in 2 minutes.*

---

## 1. Non-negotiables

1. **Works with zero API keys.** Every project has a **demo mode** that is fully
   offline and deterministic. When `GEMINI_API_KEY` (or `OPENAI_API_KEY`) is set in
   `.env`, the project upgrades to real LLM calls. Demo mode must still produce a
   complete, satisfying run — never a stub, never "TODO: add API key".
2. **Self-contained folder.** Own `README.md`, `requirements.txt`, `.env.example`,
   `.gitignore`, `tests/`. No imports from sibling projects. Duplicating a small
   `llm.py` across projects is fine and intended.
3. **Tests pass offline.** `pytest` must pass with no network and no API key.
   No test may make a real HTTP request.
4. **Minimal dependencies.** Allowed: `requests`, `flask`, `numpy`, `pandas`,
   `scikit-learn`, `matplotlib`, `pypdf`, `python-dotenv`, `pytest`. Everything
   else must be stdlib. Do NOT use langchain/llama-index/streamlit/openai SDKs —
   building the mechanics by hand is the whole point.
5. **Python 3.13**, type hints on public functions, docstrings that explain *why*,
   small focused functions. No dead code, no commented-out blocks, no debugging
   prints left behind (structured logging is fine).
6. **venv:** the repo root already has `.venv` with all allowed packages
   installed. Test with `"../../.venv/bin/python" -m pytest` from inside the
   project, or activate it. Each project still ships its own `requirements.txt`.

## 2. Folder layout (every project)

```
NN-project-name/
├── README.md           # template in section 3
├── requirements.txt    # one dep per line, pinned loosely (e.g. requests>=2.31)
├── .env.example        # GEMINI_API_KEY=... (only if the project uses an LLM)
├── .gitignore          # .env, __pycache__, .venv, outputs (project-specific)
├── <package_name>/     # the Python package (matches folder name, no digits)
│   ├── __init__.py
│   └── ...
├── tests/
│   └── test_*.py
└── (optional) data/    # bundled sample data — small, human-readable
```

## 3. README template (every project README, in this order)

```markdown
# NN. Project Name

> One-line tagline. What a friend would say in one sentence.

**Inspired by:** <which source repo/link and why>

## What it does
- bullet, bullet, bullet (concrete capabilities, not buzzwords)

## Quick start
```bash
# exact copy-paste commands, tested, from repo-root perspective
```

## How it works
ASCII architecture diagram + a numbered walkthrough of one full run
(trace the data through the system).

## Demo mode vs. real mode
Table: what happens with no key vs. with GEMINI_API_KEY.

## Project structure
Annotated file tree (one line per file).

## Explain it like I'm 19
A real-world analogy (3–6 sentences) that a non-coder would understand.

## Explain it in an interview
5 Q&A pairs: question a real interviewer asks + a strong, honest answer.

## Ideas to extend it
5 concrete next steps (each one is a sentence and doable).

## Tests
How to run them + what they cover.
```

Voice rules: second person, present tense, no marketing fluff, no emoji overload
(0–2 per README is fine, used as section markers only). Diagrams in fenced code
blocks. Every command in a README must have actually been run and verified.

## 4. LLM access convention

`llm.py` in each project exposes one function roughly like:

```python
def complete(prompt: str, *, system: str | None = None, json_mode: bool = False) -> str
```

* Reads `GEMINI_API_KEY` / `OPENAI_API_KEY` from environment (via `python-dotenv`,
  `.env` file at project root).
* Key present → real call via `requests` (Gemini REST:
  `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent`,
  or OpenAI-compatible `/v1/chat/completions`). 15 s timeout, 2 retries, clear error
  message on failure that tells the user demo mode still works.
* No key → returns from a **deterministic demo generator** (seeded, offline) that
  produces believable, useful output for that project's task. NEVER return a
  placeholder like "demo response".
* `GEMINI_API_KEY` missing → also check `.env` via dotenv; log one line:
  `[demo mode] no API key found — using offline generator`.

## 5. Demo-mode design (the make-or-break rule)

Demo mode is not a stub — it is a **parallel implementation** of the same pipeline.
Example: a RAG system in demo mode still chunks, still scores cosine similarity,
still retrieves, still answers with citations; only the *generation* step uses
extractive sentences instead of an LLM. An agent still runs its think→act→observe
loop; only the "brain" is a rule-based parser instead of a model.

If a user with no key runs the project end-to-end, they must see the same
artifacts (files, dashboards, reports) as a user with a key.

## 6. Testing bar

* Core logic covered: parsers, metrics, state machines, tool dispatch, math.
* Aim for the tests a reviewer would notice: edge cases (empty input, leap year,
  zero chunks, PSI on identical distributions = 0, max-iteration termination).
* No sleeps longer than 0.1 s, no network, no writing outside `tmp_path`.

## 7. Git

The repo root is a git repo. Commit after each project with a message like:
`feat(03-rag-studio): chunker, TF-IDF store, retrieval evals`. Never commit
`.venv/` or `.env`. (Integration/fix commits happen at the root; per-project
commits are made by the integrator.)

## 8. Quality gate (run before declaring done)

```bash
cd <project>
../../.venv/bin/python -m pytest -q          # all green
../../.venv/bin/python -m <package> --help   # CLI entry works (if CLI)
```
Then read your README top to bottom and verify every command in it works verbatim.

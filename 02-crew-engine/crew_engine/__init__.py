"""Crew Engine — a multi-agent framework written from scratch.

Three patterns, zero dependencies beyond ``requests``:

* **Sequential crew** — agents take turns: A, then B, then C.
* **Supervisor crew** — a dispatcher agent plans subtasks and assigns workers,
  looping until done or until an iteration budget runs out.
* **Reflective crew** — generator -> critic -> revise, a bounded loop that
  stops when the critic is satisfied or the refinement budget is spent.

The LLM is pluggable: with ``GEMINI_API_KEY`` agents use a real model; without
one, every agent runs a deterministic *demo brain* that performs the same
pipeline (real extraction, real assembly, real rubric scoring) so the whole
system works offline and in CI.
"""

__version__ = "1.0.0"
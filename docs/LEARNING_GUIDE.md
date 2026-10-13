# Learning Guide — interview prep for this portfolio

The portfolio is built to survive a technical interview. This guide is the
script: how to open, how to go deep on each project, and how to answer the
questions *behind* the questions. Rehearse the 2-minute version out loud;
the rest is ammunition you reach for when asked.

---

## 1. The 10-second framing

> "I built six AI/ML projects from scratch — no langchain, no SDK wrappers —
> so I understand every layer of what they do. A voice assistant, a multi-agent
> framework, a RAG pipeline, a model-monitoring system, an agent skill system,
> and a contribution-graph generator. Every one runs offline in a deterministic
> demo mode and upgrades to real Gemini calls when a key is set, and every one
> has tests. The unifying idea: the demo brain is a *parallel implementation* of
> the same pipeline, not a stub — so the whole portfolio works with zero API
> keys, in CI, and in a live demo."

Two minutes, one idea, six proofs. Then let them pick a project.

---

## 2. Cross-cutting questions (asked of almost every project)

**Q: Why "demo mode is a parallel implementation, not a stub"?**
A: Most tutorials hardcode an answer until you paste a key. I did the opposite:
the rule-based brain performs the *same computation* as the model — it extracts
real facts with sources, scores drafts on a real rubric, computes real TF-IDF
scores or PSI values. So demo mode is a complete, deterministic system I can
test offline; the LLM path is a drop-in brain with an honest fallback.

**Q: You built everything from scratch — why not just use the libraries?**
A: Three reasons. (1) *Understanding*: if I use `eval` I can't explain
arithmetic security; if I use langchain I can't explain agent loops. The
interview answer to "how does this work?" is always "here's the file."
(2) *Control*: a 50-line hand-built TF-IDF retriever is debuggable and testable;
a framework is a black box. (3) *Honesty*: a portfolio of reimplementations
proves the mechanics are mine.

**Q: How do you keep the demo deterministic for tests?**
A: No network, no randomness without a fixed seed, no wall-clock dependence
where avoidable. Where time is needed (drift windows, activity years) it's
injected as a parameter so tests freeze it. And every demo brain is tested
with `pytest` the same way the real path is — tests don't have a "demo
exception".

**Q: How did you handle the API key safety?**
A: Keys live in `.env`, which is gitignored at the root *and* per project;
`python-dotenv` loads them at runtime; and the LLM layer has an explicit no-key
contract — 01/02/05 raise a typed `LLMUnavailable` the caller catches to run the
demo brain, while 03 returns an offline completion directly. No key is ever
committed, and tests never make a real HTTP call.

**Q: What's your testing philosophy?**
A: Public behaviour over internals: rule coverage, safety guards (calculator
can't evaluate `__import__`), termination guarantees (reflective crew ≤ 2
revisions), and end-to-end CLI/Flask runs through a test client. All offline,
all fast (a few seconds per project). Tests encode the *claims* in each README.

---

## 3. Project-by-project Q&A

### 01 — Orbit Voice Assistant

**Two-minute story:** A voice-first assistant in a browser tab — mic in via the
Web Speech API, spoken replies out, zero CDNs. The demo brain is a classic NLU
pipeline: ordered regex rules classify the intent, slot extractors pull the
parameters, and a tool registry executes — with safety rails. Set a key and the
same shell runs Gemini in a bounded ReAct loop over the same tools.

**Q: Your calculator evaluates user input — how is it safe?**
A: It never calls `eval`. Python's `ast` module parses the expression into a
tree, and I only accept whitelisted node types: numbers, binary operators,
unary minus, parentheses. Names, attributes, and calls are rejected at parse
time, so `__import__('os')` can't even be evaluated. I also cap exponents and
result magnitude — deny-by-default, not a denylist.

**Q: What's the ReAct loop and why is it bounded?**
A: ReAct = reason → act (call a tool) → observe the result → repeat. The model
returns `{"tool": "...", "arguments": {...}}`, the engine executes it and feeds
back the observation, and after at most 3 rounds the model must answer. The
bound guarantees termination and caps token spend; every call is reported in
`tools_used`.

**Q: Where would this break in production?**
A: The demo brain is brittle by design — regex NLU doesn't generalize, so
paraphrases fall through to the fallback intent (it degrades gracefully). I'd
also add per-session rate limits, auth, and a proper ASR backend instead of
browser-only speech recognition. Good follow-up to volunteer: "demo mode
guarantees it answers; it doesn't guarantee it answers *well* — that's what
the model path is for."

### 02 — Crew Engine

**Two-minute story:** A multi-agent framework with three orchestration
patterns — sequential, supervisor, and reflective — all sharing a blackboard
of cited facts, artifacts, and a full audit trace. Demo brains do real work:
researchers extract source-cited sentences from a bundled corpus, writers
assemble them, and a critic scores drafts on a four-axis rubric, driving a
bounded revise loop that converges.

**Q: Why a blackboard instead of agents messaging each other?**
A: Direct messaging couples agents — everyone must agree on a protocol and the
history scatters. The blackboard decouples them: a researcher only posts facts,
a writer only reads facts, so any agent is swappable and the message log is a
built-in audit trail. One of the first things you learn debugging multi-agent
systems is that observability is everything.

**Q: What stops the reflective loop from running forever?**
A: Two guards: `max_refinements` (default 2) caps revision rounds — termination
is guaranteed by construction — and the critic is bounded by an explicit
rubric. The result object reports `refinements` and round count so convergence
is observable, and there's a test that asserts the demo converges in exactly
one revision for a mechanism topic.

**Q: How do agents avoid hallucinating facts?**
A: Architecturally: a writer only assembles facts already on the blackboard,
and every fact records its source and renders `[source: doc]` per bullet. In
LLM mode the model is limited to the same tools (`corpus_search`, `read_doc`)
and its output returns to the same blackboard — the citation discipline is
enforced by the framework, not the prompt.

### 03 — RAG Studio

**Two-minute story:** A retrieval-augmented generation pipeline built by hand:
chunking, a TF-IDF index, retrieval, generation, and an eval harness with
recall@k, MRR, and faithfulness. Demo mode runs the *real* index on the bundled
corpus — recall@3 1.00 and faithfulness 1.00 over 15 labeled questions. Setting
`GEMINI_API_KEY` upgrades query rewriting, embeddings, and generation to Gemini
behind the same interfaces, with the extractive path as an automatic fallback.

**Q: Why TF-IDF instead of vector embeddings?**
A: Embeddings need a model — either an API call or a heavy local dependency —
which breaks "offline first". TF-IDF is a pure math baseline I can implement,
test, and explain in a minute, and for evaluation you want a controllable
baseline before you swap in a better retriever. The architecture makes that a
one-line change: the retriever interface stays the same.

**Q: How do you measure whether RAG is actually helping?**
A: The eval harness: `recall@k` (did the right chunk make it into the top-k?),
`MRR` (how early did it rank?), and faithfulness (is the generated answer
grounded in the retrieved context?). Metrics first, tweaks second — without
them, "RAG works" is vibes.

### 04 — Model Watch

**Two-minute story:** Model monitoring without a framework: population
stability index (PSI) and Kolmogorov–Smirnov drift scored by hand over a
sliding window, a model registry, data generation, alerting, a Flask dashboard
(port 5104), and CLI reports — the whole "drift detection" loop a production
ML team needs, rebuilt and testable offline.

**Q: PSI vs KS — why implement both?**
A: They answer different questions. PSI is a distribution-distance statistic
with industry thresholds (interpretable bands: <0.10 stable, 0.10–0.25 warn,
≥0.25 alert); KS asks how different two cumulative distributions are
statistically. Using both catches drift that one might miss, and implementing
both by hand meant I could check them against the textbook definitions and
explain exactly what each number means.

**Q: What makes drift detection hard in practice?**
A: Three things: (1) *windows* — too short and noise alarms, too long and real
drift arrives late, so windows must be tunable; (2) *references* — what
baseline are you comparing to, and does it age? (3) *alert fatigue* — a good
system separates "drifted" from "needs human attention." I'd also say
front: monitoring your data is how you learn your model decays *before* a
dashboard shows it.

### 05 — Skill Forge

**Two-minute story:** An agent skill system from scratch: a `SKILL.md` format,
a parser (a tiny YAML-ish subset, no PyYAML), a keyword selector plus an LLM
router, token-budget prompt packing, and a CLI to list, search, pick, pack, run,
and install skills — nine bundled skills and 57 tests. It's the "tools for
agents" idea made inspectable.

**Q: What is a skill architecturally?**
A: A skill is a small, self-describing unit — instructions plus metadata in a
`SKILL.md` — that an agent can discover, select, and inject into its context.
The interesting part is *selection*: when an agent has nine skills and a token
budget, which ones fit the current task? That's the same packing problem any
long-context system faces, and it's testable in isolation.

**Q: Why build this instead of using a framework?**
A: Because "how does the agent know when to use a tool?" is the question — and
the answer (parse the manifest, score the query, pack within the budget) is
about 300 lines I can show and unit-test. It also gave me a clean mental model
for every other project's tool registry.

### 06 — GH Activity Forge

**Two-minute story:** A contribution-graph generator with deterministic
personas — random (Poisson), streak, custom — a hand-built SVG renderer using
GitHub's exact colour palette, leap-year-aware date math, a report bundle, and
an *opt-in* script that backdates empty commits, wrapped in loud ethics
warnings. I deliberately built the warning system first, because the whole
point is a demo tool that can't be mistaken for real work.

**Q: This generates fake commits — isn't that dishonest?**
A: That's exactly why the ethics layer is the most heavily tested part: the
emitter is opt-in (`--emit-git-script`), every generated script carries a
warning header, the reports state the data is demo-only, and the README opens
with the warning. The tool's purpose is rendering demo graphs and testing
contribution-graph UIs — backdating empty commits to fake a real history fails
in minutes under review, and I say so out loud.

**Q: How do you make it *look* human?**
A: Zero-commit days, quieter weekends, whole blank vacation weeks, occasional
10+ burst days — all seeded so runs are reproducible. The realism rules are
data (per-profile parameters), not hardcoded noise, so a test can assert
weekday/weekend behaviour deterministically.

---

## 4. The "what's next" answers

Have one polished answer per theme; interviewers love a road map:

- **Scale:** serve the assistant's intent model with real training data; add
  per-session budgets; make Crew Engine crews persistent with rehydratable
  trace transcripts.
- **Evaluation:** every project gets a regression suite that scores the *LLM
  path* offline (recorded model outputs) so demo and real mode stay comparable.
- **Distributed:** a shared blackboard across processes (the blackboard
  interface already is the boundary) and drift monitoring on real
  feature-streams instead of generated ones.
- **Safety:** machine-checked allowlists, output classifiers, and a human-
  in-the-loop tool in Crew Engine.

---

## 5. Answering the meta questions

**"Why these six projects?"**
They cover the AI surface an interviewer actually probes: agents (01, 02, 05),
retrieval/LLM apps (03), production/MLOps (04), and data/creative tooling (06).
All of them share the *demo-or-real* architecture, so answering one project
deeply answers all of them structurally.

**"What was the hardest debugging moment?"**
Have a real one ready, with the fix. Good candidates from this build: the
reflective crew never converging because the critic scored the draft's
citations against a *different* fact subset than the writer used (fixed by
scoring citations against the draft's own bullets); and the notes-store
silently replacing itself because `store or NotesStore()` treated an *empty
store* (which defines `__len__`) as falsy. Both are the kind of story that
proves you debug systems, not syntax.

**"What would you do differently with unlimited GPU/time?"**
Honest and short: keep the architecture, replace the deterministic brains with
fine-tuned small models, and invest in evaluation — a bigger demo corpus for
RAG and real feature streams for drift. The architecture was the valuable
part; the brain is a swap.
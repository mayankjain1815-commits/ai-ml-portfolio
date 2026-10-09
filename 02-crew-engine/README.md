# 02. Crew Engine

> A from-scratch multi-agent framework — three crew patterns (sequential, supervisor, reflective) that coordinate agents through a shared blackboard, offline or with a real Gemini model.

**Inspired by:** CrewAI / OpenAI Swarm-style orchestration (agents with roles, tools and a shared memory) and the *blackboard architecture* from classic AI — rebuilt by hand, one pattern at a time, so every design decision is explainable.

## What it does
- **Three crew patterns**: sequential (A → B → C), supervisor (planner fans work out to workers, then briefs), and reflective (writer → critic → revise, bounded loop that converges).
- **Agents with roles + tools**: each agent gets a name, role, goal, backstory, and a tool registry (corpus search, document reader, web search, clock, artifact saver). Tools are the only way agents touch the world.
- **Blackboard shared memory**: agents never talk directly — they post *cited facts*, messages, and artifacts to one board, so nothing is invented and everything is auditable.
- **Deterministic demo brains**: with no API key, researchers extract real, source-cited sentences from the bundled corpus; the writer assembles them; the critic scores against a 4-axis rubric. Same pipeline, rule-based brain.
- **LLM upgrade path**: set `GEMINI_API_KEY` and the same crews run through the Gemini REST API with a thin JSON tool-calling protocol (and honest fallback if a call fails).
- **Full audit log**: `--trace` prints every agent action, tool call, and result — the "show your work" layer.

## Quick start
```bash
cd 02-crew-engine

# All three patterns on sample topics (works offline, no key needed)
../.venv/bin/python -m crew_engine demo

# Same run with the full audit log of every agent action
../.venv/bin/python -m crew_engine demo --trace

# One reflective crew: draft -> review -> revise until the critic approves
../.venv/bin/python -m crew_engine report "Explain how neural networks learn"

# One supervisor crew: plan, fan out to 4 workers, write the briefing
../.venv/bin/python -m crew_engine supervise "Summarize the history of AI and its lessons"

# Real LLM mode (optional)
cp .env.example .env   # then put your GEMINI_API_KEY in .env
```

## How it works
```
                 ┌─────────────────────────────────────────────┐
                 │                 BLACKBOARD                  │
                 │  facts (content + source + who found it)    │
                 │  messages (full audit trail, in order)      │
                 │  artifacts (draft, plan, feedback, briefing)│
                 └───────────────▲───────────────▲─────────────┘
                                 │ reads/writes │
      SequentialCrew     SupervisorCrew    ReflectiveCrew
      ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
      │ Aria research│   │ Sana plan    │   │ writer drafts    │
      │ Bilal write  │   │ workers read │   │ critic scores it │
      │ Cleo review  │   │ Sana briefs  │   │ revise (max 2×)  │
      └──────────────┘   └──────────────┘   └──────────────────┘
```
Walkthrough of one reflective run (`report "Explain how neural networks learn"`):
1. **Research task** — the writer's demo brain scans `data/corpus/*.md`, scores every sentence by topic-word overlap, and posts the top hits to the board as facts, each tagged `[source: <doc>]`. (With a key, the model does the same job and can call `corpus_search`.)
2. **Write task** — the writer assembles the board's facts into a markdown report: title, *Key findings* (every bullet cited), and a summary. No invented sentences — only assembled ones.
3. **Critique task** — the critic scores the draft on coverage / citations / structure / relevance and writes feedback. A mechanism topic ("how", "works", "learning…") without a *How it works* section gets flagged.
4. **Revise** — the writer re-runs, now reading the latest feedback artifact; the *How it works* section appears. The critic approves, the loop stops. The result reports `refinements: 1` — proof the loop actually looped.
5. Everything the agents did is in the `--trace` transcript, and the whole run used **zero network calls** in demo mode.

## Demo mode vs. real mode
| | No API key (demo) | `GEMINI_API_KEY` set |
|---|---|---|
| Thinking | Deterministic demo brain per role (keyword research, rule-based writer, rubric critic) | The Gemini model reads each agent's role prompt and replies |
| Tool use | Demo brains don't need tools (they read the corpus directly) | Model returns `{"tool": "...", "arguments": {...}}` JSON; the engine executes and feeds back observations |
| Facts | Extracted verbatim from the bundled corpus, every fact carries `[source: doc]` | Model output, grounded via the same `corpus_search`/`read_doc` tools |
| Failure mode | Never fails — deterministic | Network/rate-limit errors fall back to the demo brain, so a run never half-completes |
| Output | Identical artifacts (draft, feedback, briefing) either way | Same artifacts, model-written |

## Project structure
```
02-crew-engine/
├── crew_engine/
│   ├── __init__.py      # package docstring + version
│   ├── llm.py           # Gemini REST via requests; raises LLMUnavailable without a key
│   ├── tools.py         # Tool/ToolRegistry + corpus_search, read_doc, web_search, now, save_artifact
│   ├── blackboard.py    # facts (with provenance), message log, artifacts
│   ├── task.py          # one unit of work; write tasks publish the standard "draft" artifact
│   ├── agent.py         # role/goal/backstory + tools; llm path with JSON tool loop, demo path by task kind
│   ├── brain.py         # the deterministic demo brains: research, write_draft, critique, plan, summarize
│   ├── crew.py          # SequentialCrew, SupervisorCrew, ReflectiveCrew + CrewResult
│   ├── trace.py         # shared audit log (the --trace transcript)
│   ├── cli.py           # report / supervise / demo subcommands
│   └── __main__.py      # python -m crew_engine
├── data/corpus/         # 4 bundled articles (history-of-ai, neural-networks, ai-in-the-world, ai-ethics)
├── tests/               # 39 tests: tools, blackboard, brains, crews, CLI
└── README.md
```

## Explain it like I'm 19
Imagine three people writing a team report in one office. Aria researches by walking to the library, photocopying pages with margin notes about *where* each fact came from, and pinning them to the office whiteboard. Bilal reads only what's pinned — never her own notes — and writes the report from it, citing each page. Cleo reads the report with a scoring sheet and leaves sticky notes: "cite page 12", "add a 'how it works' paragraph". Bilal rewrites; Cleo re-reads; when Cleo has no more sticky notes, the report ships. The whiteboard is the blackboard. The sticky notes are the artifacts. The office manager (supervisor pattern) instead pins *assignments*: "you read the history shelf, you read the ethics shelf, you write the summary." Same office, different management style — that's what the three crews are.

## Explain it in an interview
**Q: Why a "blackboard" instead of agents messaging each other directly?**
A: Direct messages couple agents — everyone has to agree on the protocol and the history is scattered. The blackboard decouples them: a researcher *only* posts facts with sources, a writer *only* reads facts. Any agent can be swapped without touching the others, and the message log is a built-in audit trail — one of the first things you notice when debugging a multi-agent system.

**Q: What stops a reflective loop from running forever?**
A: Two guards. The critic is bounded by an explicit rubric, and the loop is capped by `max_refinements` (default 2) — every draft is shipped after a fixed number of rounds regardless of approval. Termination is guaranteed by construction, not by luck. The result object also reports the round count, so it's observable.

**Q: How do the demo brains relate to the real LLM path?**
A: Same pipeline, different brain. The task carries a `kind` (research/write/critique/plan/summarize) and the agent's persona text shapes how it sounds. With no key, a rule-based brain performs the *same computation* — real extraction, real rubric scoring — so demo mode isn't a stub, it's a parallel implementation that never crashes and runs in CI.

**Q: How do you prevent agents from hallucinating facts?**
A: Two ways. Architecturally, the writer only assembles facts that are already posted to the blackboard, and every fact records its source — the draft renders `[source: doc]` per bullet, so nothing is uncited. In LLM mode, the model is limited to the same tools (`corpus_search`, `read_doc`), and its output returns to the same blackboard — the citation discipline is enforced by the framework, not the prompt.

**Q: Why would you ever use a supervisor instead of a single agent with a big prompt?**
A: Single prompts get long, unfocused, and expensive — every token is sent on every call. A supervisor splits the work so each worker gets a small, focused task and a specialized role, and outputs can be checked per subtask (each worker's facts are verifiable). It trades latency and complexity for modularity: you can reason about each worker independently and reuse them across crews.

## Ideas to extend it
- Add a **human-in-the-loop tool** that pauses a task and asks the user for input (and watch the trace show `WAIT` events).
- Add a `vote` crew pattern: three independent writers each draft, then a reviewer picks the best — a mini ensemble.
- Wire `web_search` into the demo researcher so offline uses the corpus and online adds live results with a `[web]` source tag.
- Persist a crew run: replay the trace transcript back onto a fresh blackboard to "rehydrate" a session.
- Add a small cost/step counter in the trace so LLM-mode runs report tokens and tool calls per agent.

## Tests
```bash
cd 02-crew-engine
../.venv/bin/python -m pytest -q        # 39 tests, all offline, ~0.1s
```
What they cover: tool registry and corpus integrity (search scoring, citations, unknown-doc handling); blackboard mechanics (fact dedupe with provenance, relevance filter, transcript ordering); each demo brain (research posts cited facts, writer structure, critic rubric, mechanism flagging); crew termination guarantees (reflective converges in ≤2 rounds, supervisor respects the iteration budget) and CLI end-to-end runs (demo announces `[demo mode]`, `--trace` prints the audit log, report converges to *How it works*).
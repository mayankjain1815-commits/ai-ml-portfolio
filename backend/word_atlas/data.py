"""The ten words on the landing page, with the full story behind each one.

Every record is hand-written and points at real files in this repository. The
API, the tests and the interactive panel in index.html all read from here, so
a word can never drift away from its explanation.
"""

# Aurora neon palette, shared with the landing page and the README showcase.
PALETTE = {
    "cyan": "#2DE7FF",
    "magenta": "#FF42C6",
    "lime": "#C4FF4D",
    "violet": "#8E64FF",
    "ice": "#E9F2FF",
}

PROJECTS = {
    "01": {"id": "01", "name": "Orbit Voice Assistant", "path": "01-orbit-voice-assistant",
           "readme": "01-orbit-voice-assistant/README.md"},
    "02": {"id": "02", "name": "Crew Engine", "path": "02-crew-engine",
           "readme": "02-crew-engine/README.md"},
    "03": {"id": "03", "name": "RAG Studio", "path": "03-rag-studio",
           "readme": "03-rag-studio/README.md"},
    "04": {"id": "04", "name": "Model Watch", "path": "04-model-watch",
           "readme": "04-model-watch/README.md"},
    "05": {"id": "05", "name": "Skill Forge", "path": "05-skill-forge",
           "readme": "05-skill-forge/README.md"},
    "06": {"id": "06", "name": "GH Activity Forge", "path": "06-gh-activity-forge",
           "readme": "06-gh-activity-forge/README.md"},
    "07": {"id": "07", "name": "Disaster Watch", "path": "07-disaster-watch",
           "readme": "07-disaster-watch/README.md"},
    "08": {"id": "08", "name": "SENTINEL · IoT Command", "path": "08-sentinel-iot",
           "readme": "08-sentinel-iot/README.md"},
}


def _project(project_id, role):
    item = dict(PROJECTS[project_id])
    item["role"] = role
    return item


def _anchor(path, symbol, note):
    return {"path": path, "symbol": symbol, "note": note}


WORDS = [
    {
        "slug": "rag",
        "term": "RAG",
        "title": "Retrieval-Augmented Generation",
        "category": "Retrieval",
        "color": PALETTE["cyan"],
        "tagline": "Ground the answer in text you can actually inspect.",
        "definition": (
            "Retrieval-augmented generation retrieves relevant passages from a corpus and "
            "conditions the answer on them. The model is an open-book reader, not a closed-book "
            "guesser, so every claim can be traced to a chunk."
        ),
        "why_it_matters": (
            "It converts an unverifiable paragraph into a grading problem: recall@k measures "
            "whether the right evidence was found, and faithfulness measures whether the answer "
            "stayed inside that evidence."
        ),
        "how_it_works": [
            "Ingest text and split it on paragraph/sentence boundaries with a measured overlap.",
            "Build a TF-IDF index over chunks; expand queries with a small hand-built thesaurus.",
            "Retrieve the top-k chunks by cosine similarity, then apply MMR to drop near-duplicates.",
            "Generate the answer from the selected context; the offline brain does extractive scoring.",
            "Score the pipeline with recall@k, MRR and faithfulness against a fixed question set.",
        ],
        "concepts": ["chunking", "TF-IDF", "cosine similarity", "MMR", "recall@k", "faithfulness"],
        "projects": [_project("03", "The whole pipeline: chunk → index → retrieve → generate → evaluate.")],
        "code_anchors": [
            _anchor("03-rag-studio/rag_studio/chunker.py", "chunk_document", "Boundary scoring with overlap."),
            _anchor("03-rag-studio/rag_studio/index.py", "TfidfIndex", "Hand-built sparse index and query vector."),
            _anchor("03-rag-studio/rag_studio/retriever.py", "retrieve", "Top-k plus MMR diversification."),
        ],
        "commands": [
            "cd 03-rag-studio && ../.venv/bin/python -m rag_studio demo",
            "cd 03-rag-studio && ../.venv/bin/python -m pytest -q",
        ],
        "interview_answer": (
            "I built RAG without a framework so the retrieval maths is mine: my own chunker, "
            "TF-IDF index, query expansion, MMR selection and an eval harness. The demo brain "
            "does extractive scoring, which is the same pipeline shape as the Gemini path — "
            "that is why it runs with zero keys and why recall@k is a real number, not a vibe."
        ),
        "pitfalls": [
            "A chunk that cuts a sentence in half makes a correct passage unretrievable.",
            "Plain top-k returns five copies of the same paragraph; MMR fixes that.",
            "Faithfulness has to be scored against retrieved context, not model confidence.",
        ],
        "tests": ["03-rag-studio/tests/test_chunker.py", "03-rag-studio/tests/test_retrieval.py",
                  "03-rag-studio/tests/test_evals.py"],
        "systems": ["neural"],
    },
    {
        "slug": "agents",
        "term": "AGENTS",
        "title": "Multi-Agent Crews",
        "category": "Agents",
        "color": PALETTE["magenta"],
        "tagline": "Several bounded reasoners, one shared blackboard, one audit trace.",
        "definition": (
            "An agent is a loop that observes, decides, calls a tool and records the result. "
            "A crew composes those loops — sequentially, under a supervisor, or with a critic "
            "that forces reflection — while sharing state instead of passing prose around."
        ),
        "why_it_matters": (
            "The interesting failure is not a wrong tool call; it is a crew that never converges "
            "or a critic that grades a draft its writer never saw. A shared blackboard plus a "
            "trace makes both failures inspectable."
        ),
        "how_it_works": [
            "Define agents with a role, goal and a bounded set of tools.",
            "Route tasks through SequentialCrew, SupervisorCrew or ReflectiveCrew.",
            "Write facts, artifacts and messages to one Blackboard so nobody works from stale memory.",
            "Record every thought/tool/observation in a trace for replay.",
            "In LLM mode call Gemini with JSON tool-calling; offline mode runs the same state machine.",
        ],
        "concepts": ["ReAct", "tool registry", "blackboard", "supervisor", "reflection", "trace"],
        "projects": [_project("02", "The crew engine: agents, task routing, blackboard and trace."),
                     _project("01", "A single bounded ReAct loop over browser tools.")],
        "code_anchors": [
            _anchor("02-crew-engine/crew_engine/crew.py", "ReflectiveCrew", "Writer/critic loop with a convergence cap."),
            _anchor("02-crew-engine/crew_engine/blackboard.py", "Blackboard", "Shared facts, artifacts and audit messages."),
            _anchor("01-orbit-voice-assistant/orbit_voice_assistant/chat.py", "ReAct loop", "Bounded reason-act-observe cycle."),
        ],
        "commands": [
            "cd 02-crew-engine && ../.venv/bin/python -m crew_engine demo --trace",
            "cd 02-crew-engine && ../.venv/bin/python -m pytest -q",
        ],
        "interview_answer": (
            "I implemented the orchestration myself: three crew topologies, a blackboard and a "
            "trace. The reflective crew was the hard one — it kept failing because the critic "
            "checked citations against a different fact subset than the writer used. I fixed it "
            "by scoring citations against the draft's own bullets, then encoded that as a test."
        ),
        "pitfalls": [
            "Unbounded ReAct loops burn tokens without ever converging.",
            "A critic evaluating different evidence from the writer produces endless false negatives.",
            "Passing full history between agents hides which fact came from where.",
        ],
        "tests": ["02-crew-engine/tests/test_crew.py", "02-crew-engine/tests/test_blackboard.py",
                  "02-crew-engine/tests/test_brain.py"],
        "systems": ["neural", "particles"],
    },
    {
        "slug": "mlops",
        "term": "MLOPS",
        "title": "Model Operations & Drift",
        "category": "Operations",
        "color": PALETTE["lime"],
        "tagline": "Notice the model going stale before the users do.",
        "definition": (
            "MLOps is the monitoring and registry layer around a deployed model: track input "
            "distributions, compute drift statistics, raise severity-scaled alerts and keep a "
            "versioned record of what was shipped."
        ),
        "why_it_matters": (
            "Accuracy on a frozen test set says nothing about next week's traffic. PSI and KS "
            "are cheap, explainable checks that run on every window without a label."
        ),
        "how_it_works": [
            "Generate a seeded reference and live stream so the demo is reproducible.",
            "Compute population stability index per bucket and KS distance on numeric features.",
            "Layer a regression-slope check for gradual trend, not just sudden jumps.",
            "Escalate through the AlertManager with warn/alert thresholds and cooldowns.",
            "Serve a Flask dashboard plus a registry that lists model versions and metrics.",
        ],
        "concepts": ["PSI", "KS statistic", "sliding window", "severity", "registry", "cooldown"],
        "projects": [_project("04", "Drift detection, alerting, registry and the monitoring dashboard.")],
        "code_anchors": [
            _anchor("04-model-watch/model_watch/drift.py", "psi", "Bucketed population stability index."),
            _anchor("04-model-watch/model_watch/drift.py", "ks_statistic", "Two-sample KS distance."),
            _anchor("04-model-watch/model_watch/alerts.py", "AlertManager", "Threshold, dedup and cooldown logic."),
        ],
        "commands": [
            "cd 04-model-watch && ../.venv/bin/python -m model_watch demo",
            "cd 04-model-watch && ../.venv/bin/python -m pytest -q",
        ],
        "interview_answer": (
            "I implemented PSI and KS from the formulae rather than calling a library, so I can "
            "explain the bucket choices and what each number means. A sliding window feeds a "
            "severity classifier, and the alert manager deduplicates and cools down so a single "
            "noisy batch cannot page anyone."
        ),
        "pitfalls": [
            "PSI with empty reference buckets explodes; the implementation smooths them.",
            "KS flags any large sample; thresholds must account for window size.",
            "Alert spam is worse than a missed warning — dedup and cooldown are part of the design.",
        ],
        "tests": ["04-model-watch/tests/test_core.py", "04-model-watch/tests/test_monitoring.py"],
        "systems": ["globe", "particles"],
    },
    {
        "slug": "forecast",
        "term": "FORECAST",
        "title": "Deterministic Forecasting",
        "category": "Operations",
        "color": PALETTE["violet"],
        "tagline": "Same seed, same emergency, every single demo.",
        "definition": (
            "A seeded forecast generator produces hourly weather for six monitored areas. It is "
            "not a weather service: it is a reproducible input stream that makes risk logic "
            "testable and the dashboard demo honest."
        ),
        "why_it_matters": (
            "You cannot unit-test a risk model against live weather. A deterministic forecast "
            "lets a test assert the exact hour at which a flood warning should be issued."
        ),
        "how_it_works": [
            "Seed a generator once and derive 72 hourly points per area.",
            "Model a diurnal cycle plus correlated rain, wind, humidity and pressure-driven events.",
            "Feed each hour into the rule-based risk model for flood/cyclone/heat/storm.",
            "Run the monitor orchestrator to produce forecasts, risks, alerts and incidents.",
            "Expose the resulting snapshot through JSON APIs and a Flask dashboard on port 5107.",
        ],
        "concepts": ["seeded PRNG", "hourly horizon", "diurnal cycle", "scenario replay", "risk scoring"],
        "projects": [_project("07", "Forecast generator, risk rules, alerts and the authority dashboard.")],
        "code_anchors": [
            _anchor("07-disaster-watch/disaster_watch/forecast_gen.py", "generate_forecast", "Seeded 72-hour hourly stream."),
            _anchor("07-disaster-watch/disaster_watch/monitor.py", "run_monitor", "Forecast → risk → alerts → incidents."),
        ],
        "commands": [
            "cd 07-disaster-watch && ../.venv/bin/python -m disaster_watch demo",
            "cd 07-disaster-watch && ../.venv/bin/python -m pytest -q",
        ],
        "interview_answer": (
            "The forecast is deliberately seeded. That makes the entire disaster pipeline "
            "replayable — I can assert the exact hour a warning opens and that deduplication "
            "does not emit a second one. With live weather those tests would be flaky and "
            "unreviewable."
        ),
        "pitfalls": [
            "Random noise without correlation looks nothing like a real storm.",
            "A forecast that changes between runs makes alert tests meaningless.",
            "Mixing forecast generation with risk logic couples two things that should be tested apart.",
        ],
        "tests": ["07-disaster-watch/tests/test_forecast.py", "07-disaster-watch/tests/test_risk.py",
                  "07-disaster-watch/tests/test_alerts.py"],
        "systems": ["globe"],
    },
    {
        "slug": "signals",
        "term": "SIGNALS",
        "title": "Telemetry & Signal Processing",
        "category": "Operations",
        "color": PALETTE["cyan"],
        "tagline": "Noisy sensor readings become evidence, not panic.",
        "definition": (
            "Signals are the validated telemetry frames arriving from sensors — temperature, "
            "rain, water level, vibration, AQI, battery and radio quality. Processing means "
            "validating, normalising, storing and turning them into a state a human can read."
        ),
        "why_it_matters": (
            "A single spike is noise; a rising river over twelve packets is evidence. The "
            "processing layer is where that distinction is made before any alert exists."
        ),
        "how_it_works": [
            "Validate each ingress packet against a schema; reject impossible ranges.",
            "Persist to native node:sqlite with an index on node and timestamp.",
            "Derive per-node history windows and a 0–100 risk score per hazard.",
            "Push a compact snapshot over WebSocket so the UI never polls.",
            "Keep the raw packet and the derived score side by side for audit.",
        ],
        "concepts": ["ingress validation", "sqlite", "windowing", "WebSocket", "hysteresis"],
        "projects": [_project("08", "Telemetry ingress, store, simulator and realtime snapshot."),
                     _project("04", "Model input streams and drift signal windows.")],
        "code_anchors": [
            _anchor("08-sentinel-iot/server/app.js", "createApp", "Validated telemetry ingress and read APIs."),
            _anchor("08-sentinel-iot/server/realtime.js", "isAuthorizedGateway", "Authorised WebSocket upgrades."),
            _anchor("04-model-watch/model_watch/stream.py", "generate_stream", "Seeded live feature stream."),
        ],
        "commands": [
            "cd 08-sentinel-iot && npm ci && npm test",
            "cd 08-sentinel-iot && npm run dev",
        ],
        "interview_answer": (
            "Signals are validated at the edge of the API and stored in node:sqlite so the "
            "risk engine and the UI read the same transaction boundary. I keep raw readings "
            "and derived scores together — that is what makes an alert explainable later."
        ),
        "pitfalls": [
            "Trusting a sensor packet without range checks poisons every downstream score.",
            "Polling a dashboard wastes resources; WebSocket push keeps it honest.",
            "Correlated readings must be simulated or hysteresis can never be tested.",
        ],
        "tests": ["08-sentinel-iot/tests/telemetry.test.js", "08-sentinel-iot/tests/validation.test.js",
                  "08-sentinel-iot/tests/realtime.test.js"],
        "systems": ["particles", "globe"],
    },
    {
        "slug": "skills",
        "term": "SKILLS",
        "title": "Agent Skill Packaging",
        "category": "Agents",
        "color": PALETTE["magenta"],
        "tagline": "Capabilities as small, routable, budgeted documents.",
        "definition": (
            "A skill is a SKILL.md file with frontmatter and a body. A selector chooses which "
            "skills matter for a prompt, a packer fits them into a token budget, and a runner "
            "executes the chosen procedure."
        ),
        "why_it_matters": (
            "It turns 'the model knows tools' into a versioned, inspectable catalogue. Token "
            "budgets are explicit, so a prompt cannot silently blow past its context window."
        ),
        "how_it_works": [
            "Parse frontmatter with a tiny YAML-ish subset — no PyYAML dependency.",
            "Score skills with a keyword selector; upgrade to an LLM router when a key exists.",
            "Estimate tokens and pack selected skills into a fixed budget with a priority order.",
            "Run the packed prompt through the same executor in demo and live mode.",
            "Expose everything through a CLI: list, search, pick, pack, run, install.",
        ],
        "concepts": ["frontmatter", "keyword routing", "token budget", "prompt packing", "CLI"],
        "projects": [_project("05", "Skill loader, selector, packer, runner and CLI.")],
        "code_anchors": [
            _anchor("05-skill-forge/skill_forge/loader.py", "load_skill", "Frontmatter + body parsing."),
            _anchor("05-skill-forge/skill_forge/selector.py", "KeywordSelector", "Offline skill routing."),
            _anchor("05-skill-forge/skill_forge/packer.py", "pack", "Token-budget prompt assembly."),
        ],
        "commands": [
            "cd 05-skill-forge && ../.venv/bin/python -m skill_forge demo",
            "cd 05-skill-forge && ../.venv/bin/python -m pytest -q",
        ],
        "interview_answer": (
            "Skills are files, not registry code. I parse the frontmatter myself, route with "
            "keywords offline or an LLM when a key is present, and pack under an explicit token "
            "budget. Nine bundled skills and fifty-seven tests cover the whole path."
        ),
        "pitfalls": [
            "A greedy packer can fill the budget with one verbose skill.",
            "Frontmatter parsers that accept too much syntax become a security surface.",
            "Routing must degrade to keywords when the LLM is unavailable.",
        ],
        "tests": ["05-skill-forge/tests/test_selector.py", "05-skill-forge/tests/test_packer.py",
                  "05-skill-forge/tests/test_skill.py"],
        "systems": ["neural"],
    },
    {
        "slug": "risk",
        "term": "RISK",
        "title": "Explainable Risk Scoring",
        "category": "Operations",
        "color": PALETTE["magenta"],
        "tagline": "Every point in the score has a name and a number.",
        "definition": (
            "Risk scoring converts several continuous signals into a 0–100 index and a band. "
            "The implementation is transparent: each hazard contributes named points, a "
            "compound-hazard bonus applies when several fire together, and SOS overrides."
        ),
        "why_it_matters": (
            "An operator at 2 a.m. needs to know why an area is critical. A black-box classifier "
            "might be more accurate on paper, but it cannot answer that question in the room."
        ),
        "how_it_works": [
            "Ramp each raw measurement from an onset to a saturation threshold.",
            "Turn ramps into named point contributions per hazard (flood, landslide, air, heat).",
            "Add a compound bonus when multiple hazards cross their onset together.",
            "Clamp to 0–100, map to a band, and keep the contribution breakdown for the API.",
            "Open, escalate and resolve alerts with hysteresis on (node, hazard) keys.",
        ],
        "concepts": ["ramp", "weighted contribution", "compound hazard", "band", "hysteresis"],
        "projects": [_project("07", "Rule-weighted risk index over forecast hours."),
                     _project("08", "Continuous per-node risk engine with breakdown and alerts.")],
        "code_anchors": [
            _anchor("07-disaster-watch/disaster_watch/risk_model.py", "score_forecast", "Weighted rule score over forecast hours."),
            _anchor("08-sentinel-iot/server/risk-engine.js", "assessRisk", "Transparent 0–100 score with factors."),
        ],
        "commands": [
            "cd 07-disaster-watch && ../.venv/bin/python -m disaster_watch demo",
            "cd 08-sentinel-iot && npm test",
        ],
        "interview_answer": (
            "I chose rules over a trained model because the score has to be auditable. Every "
            "hazard contributes named points, the compound bonus is explicit, and the API "
            "returns the breakdown. The weights are data, so I can unit-test them at their "
            "boundaries instead of hoping a model behaves."
        ),
        "pitfalls": [
            "Unclamped contributions produce nonsense scores outside the training range.",
            "Without hysteresis a noisy sensor makes alerts flap every few packets.",
            "A score without its breakdown is useless to an operator.",
        ],
        "tests": ["07-disaster-watch/tests/test_risk.py", "08-sentinel-iot/tests/risk-engine.test.js",
                  "08-sentinel-iot/tests/api.test.js"],
        "systems": ["globe", "neural"],
    },
    {
        "slug": "offline",
        "term": "OFFLINE",
        "title": "Zero-Key Operation",
        "category": "Architecture",
        "color": PALETTE["lime"],
        "tagline": "The whole portfolio runs with no network and no secrets.",
        "definition": (
            "Offline mode means every project has a deterministic local implementation of the "
            "same pipeline the live model runs. It is a parallel implementation, not a stub or "
            "a cached response."
        ),
        "why_it_matters": (
            "CI can verify every claim without API keys, a reviewer can run the demo on a plane, "
            "and the fallback is never a dead end when a provider is down."
        ),
        "how_it_works": [
            "Wrap model calls behind one interface with two implementations: live and deterministic.",
            "Seed randomness and label every generated number as demo data.",
            "Run the same tests against the offline path in CI on every push.",
            "Upgrade with GEMINI_API_KEY; keep the offline brain as the honest fallback.",
            "Vendor no runtime assets — no CDN fonts, scripts or external images in the demos.",
        ],
        "concepts": ["demo mode", "determinism", "seeded data", "CI without secrets", "fallback"],
        "projects": [dict(_project(pid, "Runs fully offline with seeded data.")) for pid in
                     ("01", "02", "03", "04", "05", "06", "07", "08")],
        "code_anchors": [
            _anchor("docs/BUILD_SPEC.md", "Non-negotiables", "The zero-key rule written down."),
            _anchor(".github/workflows/tests.yml", "test matrix", "Every suite runs in CI with no secrets."),
        ],
        "commands": [
            "for p in 0*; do (cd \"$p\" && ../.venv/bin/python -m pytest -q) 2>/dev/null; done",
            "cd 08-sentinel-iot && npm test",
        ],
        "interview_answer": (
            "Offline is an architectural constraint, not a feature flag. Each project has a "
            "real deterministic brain that performs the same steps as the live model, so the "
            "tests assert real behaviour with zero keys. Set a key and only the final call "
            "changes."
        ),
        "pitfalls": [
            "A fallback that returns canned text proves nothing and fails under review.",
            "Unseeded randomness makes CI flaky and demos unrepeatable.",
            "Secrets in CI turn an offline suite into a network-dependent one.",
        ],
        "tests": [".github/workflows/tests.yml"],
        "systems": ["particles", "globe", "neural"],
    },
    {
        "slug": "demo",
        "term": "DEMO",
        "title": "Demoable by Design",
        "category": "Architecture",
        "color": PALETTE["violet"],
        "tagline": "Two minutes, one command, no setup ritual.",
        "definition": (
            "Every project ships a single demo command that produces a complete, satisfying run "
            "with visible intermediate state — a trace, a dashboard, a report — rather than a "
            "single answer."
        ),
        "why_it_matters": (
            "A demo is the most compressed form of an explanation. If it needs a key, a database "
            "and three terminals, nobody will run it, and the project stops being evidence."
        ),
        "how_it_works": [
            "Expose one obvious entry point per project: python -m <pkg> demo or npm run dev.",
            "Seed the input so the output is identical on every machine.",
            "Print or render the intermediate steps, not just the final result.",
            "Ship a README command that can be copy-pasted from the landing page.",
            "Keep the demo code on the same path as the real code, not a separate toy implementation.",
        ],
        "concepts": ["entry point", "seeded scenario", "visible trace", "copy-paste command", "two-minute story"],
        "projects": [dict(_project(pid, "One-command demo with visible intermediate state.")) for pid in
                     ("01", "02", "03", "04", "05", "06", "07", "08")],
        "code_anchors": [
            _anchor("docs/LEARNING_GUIDE.md", "Project-by-project Q&A", "A two-minute story for each project."),
            _anchor("index.html", "project cards", "Every card links to its own README."),
        ],
        "commands": [
            "cd 02-crew-engine && ../.venv/bin/python -m crew_engine demo --trace",
            "cd 07-disaster-watch && ../.venv/bin/python -m disaster_watch demo",
        ],
        "interview_answer": (
            "I designed the demo first. Each project has one command, a seeded scenario and a "
            "visible trace, so I can hand an interviewer a run they can reproduce in two minutes. "
            "The demo path and the live path share the same code; only the final model call differs."
        ),
        "pitfalls": [
            "A demo that hides its intermediate steps cannot be defended.",
            "Different commands per project destroy the portfolio's rhythm.",
            "A canned output looks impressive once and collapses under a follow-up question.",
        ],
        "tests": ["docs/LEARNING_GUIDE.md"],
        "systems": ["neural", "particles"],
    },
    {
        "slug": "iot",
        "term": "IOT",
        "title": "IoT Early-Warning Command",
        "category": "Operations",
        "color": PALETTE["cyan"],
        "tagline": "From a LoRa packet to an evacuation order, end to end.",
        "definition": (
            "An Internet-of-Things command system for a three-node ESP32/LoRa network: telemetry "
            "ingress, risk scoring, alert escalation, WebSocket push, an offline vector map and "
            "an authority console that can act on what it sees."
        ),
        "why_it_matters": (
            "It is the only project where the model is just one component. The hard problems are "
            "state, authorisation, deduplication and an operator loop that never loses an audit "
            "trail."
        ),
        "how_it_works": [
            "Validate telemetry from the gateway and persist it to native node:sqlite.",
            "Score flood, landslide, air quality and heat continuously on 0–100 with factors.",
            "Dedup alerts by (node, hazard), escalate and require two clean packets to resolve.",
            "Push snapshots over WebSocket to a React/Leaflet dashboard with a bundled offline map.",
            "Let an authorised operator acknowledge, override with expiry, evacuate, sound the siren "
            "and write an immutable incident record.",
        ],
        "concepts": ["ESP32", "LoRa", "node:sqlite", "WebSocket", "authority console", "incident log"],
        "projects": [_project("08", "The complete command platform, Node 22 + React 19.")],
        "code_anchors": [
            _anchor("08-sentinel-iot/server/app.js", "createApp", "API, command routes and gateway auth."),
            _anchor("08-sentinel-iot/server/risk-engine.js", "assessRisk", "Transparent hazard scoring."),
            _anchor("08-sentinel-iot/tests/api.test.js", "api suite", "38 offline tests for the full loop."),
        ],
        "commands": [
            "cd 08-sentinel-iot && npm ci && npm test",
            "cd 08-sentinel-iot && npm run dev",
        ],
        "interview_answer": (
            "SENTINEL is the systems project: node:sqlite gives one transaction boundary with no "
            "infrastructure, a WebSocket pushes snapshots instead of polling, and alerts use "
            "hysteresis so a noisy sensor cannot flap. The authority console closes the loop — "
            "acknowledge, override with an expiry, evacuate, and every action lands in an "
            "immutable incident log."
        ),
        "pitfalls": [
            "Using a hosted map breaks the offline guarantee; the basemap is local vector data.",
            "Command routes need real auth and role checks, not a trusting header.",
            "Alert flapping on correlated sensor noise destroys operator trust.",
        ],
        "tests": ["08-sentinel-iot/tests/api.test.js", "08-sentinel-iot/tests/risk-engine.test.js",
                  "08-sentinel-iot/tests/telemetry.test.js"],
        "systems": ["globe", "particles"],
    },
]


REQUIRED_FIELDS = (
    "slug", "term", "title", "category", "color", "tagline", "definition",
    "why_it_matters", "how_it_works", "concepts", "projects", "code_anchors",
    "commands", "interview_answer", "pitfalls", "tests", "systems",
)


def all_words():
    """Return every word record (a fresh shallow copy so callers cannot mutate data)."""
    return [dict(word) for word in WORDS]


def get_word(slug):
    """Return one word record, or None when the slug is unknown."""
    for word in WORDS:
        if word["slug"] == slug.lower():
            return dict(word)
    return None


def related_words(slug):
    """Return slugs sharing a category or a project with the given word."""
    word = get_word(slug)
    if word is None:
        return []
    mine_projects = {p["id"] for p in word["projects"]}
    result = []
    for other in WORDS:
        if other["slug"] == word["slug"]:
            continue
        shared_projects = mine_projects & {p["id"] for p in other["projects"]}
        if other["category"] == word["category"] or shared_projects:
            result.append({
                "slug": other["slug"], "term": other["term"],
                "color": other["color"], "reason":
                    "same category" if other["category"] == word["category"]
                    else f"shares project {', '.join(sorted(shared_projects))}",
            })
    return result

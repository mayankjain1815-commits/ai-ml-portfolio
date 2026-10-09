# 04. Model Watch

> An MLOps monitoring system for a churn model, built from first principles: PSI and KS drift detection by hand, sliding-window alerting, a versioned model registry, and a Flask dashboard — all offline and deterministic.

**Inspired by:** production ML monitoring platforms (Evidently AI, WhyLabs, Arize) and the classical tools those platforms wrap (population stability index from credit scoring, two-sample Kolmogorov–Smirnov, control-chart alerting) — rebuilt so the math and the alert loop are visible instead of hidden behind a SaaS dashboard.

## What it does

- **Generates a churn dataset with known ground truth.** `data_gen` samples realistic customer features, labels them with an explicit `P(churn | x)` rule, and provides a parametrized `shift()` that bends the input distribution in a controlled direction — so "drift" in this project is *engineered and measurable*, not vibes.
- **Trains real models** (logistic regression vs. random forest on the same split), picks the winner by ROC-AUC, and freezes it into a **versioned registry** — a pickled estimator plus a manifest entry carrying metrics, hyperparameters, feature names, and a SHA-256 hash of the training data.
- **Simulates 60 days of production traffic** with a deliberate three-phase story: normal (same distribution as training) → covariate drift (inputs move, the rule stays correct) → concept drift (the rule itself changes, so accuracy decays). Labels arrive 2 days late, the way churn actually becomes known.
- **Detects drift by hand.** PSI is computed against the training distribution's quantile bins (identical distributions → exactly 0.0), the two-sample KS statistic is computed from empirical CDFs (no scipy), and both feed a `ok / warn / alert` classifier with documented thresholds.
- **Tracks concept drift** as a sliding 14-day regression slope over live accuracy/F1, with a confirmation streak so one noisy day never pages anyone.
- **Deduplicates alerts** across a 24-hour rolling window per `(feature, severity)` — paging once and counting its duration, never re-paging every batch — with a pluggable `notify()` seam (the exactly-one place a Slack/webhook `requests.post` goes) and both a machine-readable `alerts.json` and a human `alerts.log`.
- **Shows everything** in a Flask dashboard (port **5104**) with server-rendered HTML, matplotlib PNGs, and JSON API endpoints, plus a plain-text CLI report.

## Quick start

```bash
cd 04-model-watch

# full pipeline: train → register → simulate 60 days → report
../.venv/bin/python -m model_watch demo

# the human-facing dashboard (port 5104)
../.venv/bin/python -m model_watch dashboard      # → http://127.0.0.1:5104

# other commands
../.venv/bin/python -m model_watch train          # train + register only
../.venv/bin/python -m model_watch simulate --days 60
../.venv/bin/python -m model_watch report

# tests (offline)
../.venv/bin/python -m pytest -q
```

## How it works

```
                     ┌─────────────────────────── training side ───────────────────────────┐
   data_gen.py       │  generate(12k rows, seed) → train two models → winner by ROC-AUC │
   (synthetic,       │        │                                                            │
    deterministic)   │        ▼                                                            │
                     │  registry/  model_v1.pkl + manifest.json (metrics, hash, features)  │
                     └──────────────────────────────────────────────────────────────────────┘

                     ┌────────────────────────── monitoring side ──────────────────────────┐
   stream.py         │  day 1..60: batch of 200 rows, phase ramps normal→covariate→concept │
   (simulated        │        │                                                             │
    prod traffic)    │        ▼                                                             │
   monitor.py        │  predict → stash (labels +2 days late) → PSI & KS per feature        │
                     │  → trend slope of accuracy/F1 → escalate to alerts                   │
                     │        │                                                             │
                     │        ▼                                                             │
   alerts.py         │  dedup per (feature, severity) within 24h → alerts.json + alerts.log │
                     │        │                                                             │
                     │        ▼                                                             │
   dashboard.py      │  Flask :5104  →  PSI bars, accuracy trend, reference-vs-current     │
                     └──────────────────────────────────────────────────────────────────────┘
```

Walkthrough of one simulated day (say day 30, mid concept-drift):

1. `StreamSimulator` draws that day's 200 customers with the phase's RNG seed (`[seed, day]` → reproducible), applies the covariate-shift magnitude ramped for that day, and labels them under the phase's churn rule (`v1` walked in days 1–19, `v2` from day 45 onward — drift is a *changing boundary*, not just a changing input).
2. The monitor scores every row with the registered model, stashes predictions against the day's labels, and measures **PSI** (training quantiles vs today's values) and **KS** (max gap between empirical CDFs) for all nine features.
3. `classify()` labels each value `ok/warn/alert`; severe ones go to `AlertManager`, where `(feature, severity)` dedup collapses repeats within 24 simulated hours into one record whose `count` rises.
4. Labels for day 28 finally arrive (2-day delay), so the monitor appends an accuracy/F1 point to the trend, fits the 14-day regression slope, and — once the slope has stayed past its threshold for 2 consecutive evaluations — raises a `model_performance` alert.
5. `monitor.json` (and CSV + alerts) land in `runs/latest/`; the dashboard reads them and renders the charts; `report` prints the same data as text.

## Offline run vs. a real deployment

This project is offline-first *by design* — there is no API key to add because the whole loop is the point. "Real mode" means pointing the same pipeline at real traffic:

| | Offline demo (what you run here) | A real deployment (same code, real inputs) |
|---|---|---|
| Input stream | `StreamSimulator`: deterministic, engineered 3-phase story | Real feature rows from a production system |
| Reference distribution | Regenerated from the registry's `dataset_seed`/`n_rows` | The actual training snapshot (or its hash) |
| Model | Trained on synthetic data (`train`) | Fitted on real labeled data, registered the same way |
| Alerts | Printed to `alerts.log` + `alerts.json` | The same records, plus one real `notify()` webhook |
| Determinism | Fully deterministic, CI-testable | Real world, by definition not deterministic |

The registry, drift math, alert dedup, and dashboard don't care which side the rows come from — that boundary is the whole design.

## Project structure

```
04-model-watch/
├── model_watch/
│   ├── __init__.py      # package docstring + version
│   ├── data_gen.py      # synthetic churn data: sampling, P(churn|x), parametrized shift()
│   ├── train.py         # race LR vs RF, hand-check the winner's metrics, hash the dataset
│   ├── registry.py      # versioned model store: pickle + manifest + provenance
│   ├── stream.py        # 60-day simulated production stream with 3 engineered phases
│   ├── drift.py         # PSI, two-sample KS, slope-trend severity — all by hand
│   ├── metrics.py       # accuracy/precision/recall/F1/ROC-AUC from first principles
│   ├── monitor.py       # the loop: observe batches, measure, escalate, persist, report
│   ├── alerts.py        # dedup window, alerts.json/log, pluggable notify() seam
│   ├── dashboard.py     # Flask app: charts + /api/metrics /api/drift /api/alerts
│   ├── cli.py           # train / simulate / report / dashboard / demo
│   ├── __main__.py      # python -m model_watch …
│   └── templates/       # index.html (server-rendered, no CDN)
├── tests/               # 24 tests: drift math, registry, dedup, full monitoring loop, API
└── README.md
```

`registry/` and `runs/latest/` are regenerated by the CLI and gitignored.

## Explain it like I'm 19

Picture a doctor checking whether your medication still works. Every day they measure your vitals (the features), compare them to the day you were prescribed (the reference), and flag anything that's drifted far from baseline — a *PSI check* is their "how different is your bloodwork today vs. then" score. They also track how you're actually doing over two weeks: one bad day is noise, but a steady slide in your vitals is a real problem that deserves a call. And they never call your whole family for every small change — same symptom within a day is one ticket, not five. Model Watch is that doctor for a machine-learning model: it watches the inputs (is the world still what the model learned?), watches the outcomes (is the model still right?), and pages someone only when the picture has genuinely moved.

## Explain it in an interview

**Q: Why did you implement PSI and KS by hand instead of using scipy or Evidently?**
A: Two reasons. First, the formulas are the interesting part — PSI is just Σ (actual−expected)·ln(actual/expected) over the reference distribution's quantile bins, and a two-sample KS statistic is the max gap between two empirical CDFs; each is ~15 lines and I can defend every one of them, including edge cases (identical distributions → exactly 0, constant features → 0 or ∞). Second, scipy would make the offline/CI story longer, and a library call doesn't teach anything at an interview. My tests verify the hand math against scikit-learn's versions.

**Q: What is covariate drift vs. concept drift, and how does your stream separate them?**
A: Covariate drift is the *inputs* moving while the true rule stays the same — the model's decision boundary is still correct, it just receives different data; I engineer it as a ramped `shift()` on the feature distribution. Concept drift is the *rule itself* changing — I swap the true `P(churn|x)` from v1 to v2 so long-tenure customers start churning, and the model's boundary is genuinely wrong. The stream is phase-engineered so a monitor run demonstrates both, and the report labels which phase each day belongs to.

**Q: Your monitor says performance decayed. How can you claim that when labels arrive late?**
A: Because the monitor is built around the delay instead of ignoring it. Predictions are stashed with the day they were made; labels arrive 2 days later (the configurable `label_delay`); only then is that day's accuracy point appended to the sliding trend. So "live" metrics in the dashboard are computed on the trailing window of *matured* labels — a 60-day mean would hide last week, and the report tells you exactly how late the labels are.

**Q: How do you prevent alert fatigue?**
A: Three mechanisms. (1) *Dedup window:* the same `(feature, severity)` recurring within 24h collapses into one record with a rising count — paging once and counting its duration, never per-batch. (2) *Confirmation streak:* concept-drift needs the slope past its threshold for 2 consecutive evaluations, because one noisy day is not an outage. (3) *Escalation honesty:* severity changes always fire, because a worsening condition is a new fact, not a repeat. The `notify()` seam is the single place a webhook would go, so routing policy stays in one function.

**Q: What does the registry give you beyond a pickle file?**
A: Provenance and reproducibility. Each version's manifest records the algorithm, hyperparameters, metrics, feature names, dataset seed/row count, and a SHA-256 of the training frame. The monitor *rebuilds* the PSI reference distribution from that seed instead of shipping a 12k-row CSV, and the hash proves it's the same data the model saw. That's the difference between "I saved a model" and "I can reproduce why this version exists."

## Ideas to extend it

- Add a **live mode**: a `notify()` webhook to Slack + a consumer that ingests real feature rows instead of the simulator.
- Add **alert recovery**: a record that stays silent for N days after its last event closes on its own.
- Add **feature attribution drift** — SHAP-style spreads per feature, so you see *why* PSI moved, not just that it did.
- Add a **promotion gate**: only auto-promote a candidate model if its drift profile is better than the incumbent's.
- Add **drift prediction**: fit the PSI time series and forecast when a feature crosses `alert` — monitoring that looks ahead.

## Tests

```bash
cd 04-model-watch
../.venv/bin/python -m pytest -q        # 24 tests, all offline, ~3s
```

What they cover: every metric hand-computed vs. scikit-learn on toy and random inputs; PSI = 0 on identical distributions, grows with shift magnitude, degenerate constant features; KS on known values; seeded generation determinism; registry round-trip and version monotonicity; alert dedup within a rolling window, fresh record after expiry, escalation as a new record, "ok" ignored, persistence across managers; and an end-to-end monitoring run in `tmp_path` — three phases observed, artifacts written, report rendered, dashboard API serving.
# 01. Orbit — Voice Assistant

> A voice-first assistant you talk to in a browser tab: Web Speech API in, spoken replies out, zero CDNs, fully offline. Demo brain by default; real Gemini replies when `GEMINI_API_KEY` is set.

**Inspired by:** everyday voice assistants (Siri/Google Assistant) plus the classic **ReAct** ("Reason + Act") tool-loop pattern — rebuilt from scratch as an explainable pipeline: *intent detection → slot filling → tool dispatch*, and, in LLM mode, a bounded think→act→observe loop over the same tool registry.

## What it does

- **Speak or type.** The frontend uses the Web Speech API (`SpeechRecognition` for mic input, `speechSynthesis` for spoken replies) with a plain-text fallback. No CDN, no analytics, no API key needed — it works with the network off.
- **A deterministic demo brain.** `DemoBrain` is a small, real NLU pipeline: ordered regex rules classify the **intent**, slot extractors pull out the *expression / note text / app name / file name / query*, and a tool registry executes. The API response reports `intent` and `tools_used` so you can see the whole decision.
- **A real tool layer, with safety rails.** The calculator parses user arithmetic with the `ast` module and *whitelists* node types (`__import__('os')` fails at parse time; exponents are capped); `read_file` only reads the bundled `data/` directory and blocks traversal; `open_app` launches only allowlisted macOS apps; `web_search` is best-effort and never crashes offline.
- **Memory that persists.** Notes are saved to a JSON file (`runs/notes.json`, gitignored) and survive restarts; a per-session ring buffer remembers the last few turns so follow-ups land.
- **LLM upgrade path.** With a key, the same shell calls the Gemini REST API in a ReAct loop — model returns `{"tool": "...", "arguments": {...}}`, the engine executes, feeds back the observation, repeats (max 3 rounds), and finally answers. Any failure honestly falls back to the demo brain.
- **A Flask API.** `POST /api/chat`, `GET /api/mode`, `GET /api/notes` — and `GET /` serves the whole frontend.

## Quick start

```bash
cd 01-orbit-voice-assistant

# Serve the assistant (works offline, no key needed)
../.venv/bin/python -m orbit_voice_assistant        # opens http://127.0.0.1:5101

# Custom port / no auto-open
../.venv/bin/python -m orbit_voice_assistant --port 5101 --no-browser

# Tests (offline)
../.venv/bin/python -m pytest -q

# Real LLM mode (optional)
cp .env.example .env   # then put your GEMINI_API_KEY in .env
```

Open the page, tap 🎤 and talk, or type. Try the chips: *time, math, remember, notes, read a file, open an app.* The mode badge in the header shows which brain is answering.

## How it works

```
 browser tab (Web Speech API)            Flask API             brains                 tools
 ┌──────────────────────────┐      ┌────────────────┐   ┌──────────────┐   ┌────────────────────┐
 │ mic/SpeechRecognition → ─┼─text─▶ POST /api/chat ──▶ │ DemoBrain     │──▶│ calculator (AST    │
 │  speechSynthesis ◀── ────┼─text─ ...            ◀─── │  (rules)      │   │  whitelist)        │
 │  chat bubbles ◀───────── ─┼─json─{reply,intent, │    │ LLM (Gemini)  │──▶│ add_note/list/     │
 │                          │       mode,tools}   │    │  ReAct loop   │   │  delete_note (json)│
 │  notes panel ◀────────── ─┼─json─ GET /api/notes│    │  (max 3 turns)│   │ open_app (allowlist)│
 └──────────────────────────┘      └────────────────┘   └──────────────┘   │ read_file (bundled │
                                                                           │  data/ only)       │
                                                                           │ web_search (best-  │
                                                                           │  effort, offline OK)│
                                                                           └────────────────────┘
```

Walkthrough of one message — `"what is 12 * 8"`:
1. The browser POSTs it to `/api/chat` with a `session_id`; the pipeline collapses whitespace.
2. `DemoBrain` runs its ordered rules. `identity → help → time → notes_* → open_app → read_file → web_search → math → greet` — the *math* rule matches and the slot extractor pulls out the expression `12 * 8`. (Order is deliberate: `"what is your name"` must hit `identity` before math gets a chance, while `"hi, what is 2+2"` still reaches math.)
3. The `calculator` tool parses it with `ast`, evaluates it against the whitelisted operator table, and returns `12 * 8 = 96`.
4. The reply is wrapped in `{"reply": ..., "intent": "math", "mode": "demo", "tools_used": ["calculator"]}`, the turn is stored in session memory, and the browser speaks it aloud: *"12 times 8 equals 96."*

With a key set, step 2 becomes a Gemini call; if the model asks for a tool, the engine runs it and feeds back the observation — same registry, same reply shape.

## Demo mode vs. real mode

| | No API key (demo) | `GEMINI_API_KEY` set |
|---|---|---|
| Brain | `DemoBrain`: ordered regex rules + slot extraction | Gemini REST API via `requests` |
| Tool use | Rules call the registry directly | Model returns `{"tool","arguments"}` JSON; engine executes, feeds back, loops (≤3) |
| Determinism | Fully deterministic, testable in CI | Model output varies |
| Failure mode | Never fails | Network/rate-limit errors fall back to the demo brain — a run never half-completes |
| Frontend | Identical either way | Identical either way (`/api/mode` badge shows which) |

## Project structure

```
01-orbit-voice-assistant/
├── orbit_voice_assistant/
│   ├── __init__.py      # package docstring + version
│   ├── llm.py           # Gemini REST via requests; LLMUnavailable without a key
│   ├── memory.py        # NotesStore (persistent JSON) + SessionMemory (ring buffer)
│   ├── tools.py         # Tool/ToolRegistry + calculator (AST-whitelisted), notes, apps, files, search
│   ├── intents.py       # DemoBrain: ordered intent rules, slot fillers, dispatch
│   ├── chat.py          # pipeline: session -> demo/LLM brain -> {reply, intent, mode, tools_used}
│   ├── app.py           # Flask factory: /, /api/chat, /api/mode, /api/notes
│   ├── cli.py           # serve on 5101, open the browser
│   ├── __main__.py      # python -m orbit_voice_assistant
│   └── static/          # index.html, app.js (Web Speech API), style.css — no CDN
├── data/                # bundled files the assistant can read (quick-tips, project-overview)
├── tests/               # 41 tests: intents, tools, memory, Flask end-to-end
└── README.md
```

## Explain it like I'm 19

Picture a receptionist with a cheat sheet of phrases. You say *"what is 12 times 8"* — they glance at the sheet: that's a *math* phrase, so they pull out the calculator they're trusted with (it only does arithmetic — it can't run code, so there's no way for a weird phrase to trick it). You say *"remember the demo is Friday"* — that's a *save* phrase, they write it in their diary and can read it back on request. You say *"open calculator"* — a *launch* phrase, but their list of apps they're allowed to open is short and fixed (an allowlist), so a random app name gets a polite no. Every answer they give, they can show you which rule on the sheet fired. That's Orbit: a receptionist whose cheat sheet is ten regexes, whose tools have safety rails, and who — if you hand them a real brain (an API key) — still uses the same desk, the same tools, and the same ways of answering.

## Explain it in an interview

**Q: How does the demo brain actually understand anything?**
A: It doesn't "understand" — it *classifies*. Intent detection is an ordered list of regex rules; the first match wins, and the order is deliberate and unit-tested (identity before math, math before greet). Slot extraction then pulls the parameters out of the matched region — the arithmetic expression, the note text, the app name. It's the classic NLU pipeline from any NLP course, implemented in ~150 lines, and because it's deterministic it's fully testable in CI.

**Q: Why is the calculator safe? You let users type arbitrary expressions.**
A: I never call `eval`. The expression is parsed with Python's `ast` module into a syntax tree, and I only accept **whitelisted** node types: numbers, binary operators (`+ - * / ** %`), unary minus, and parentheses — everything else (names, attribute access, calls) is rejected at parse time, so `__import__('os')` can't even be evaluated. On top of that I cap exponents and result magnitude so nobody asks for a 300 MB integer.

**Q: What's the ReAct pattern and why cap it?**
A: ReAct = the model *reasons*, *acts* by calling a tool, and *observes* the result — then reasons again, until it has what it needs to answer. I bound the loop to 3 think→act→observe rounds so a confused model can't spend forever (and burn tokens) churning; after three rounds it must answer. Termination by construction, and every tool call lands in `tools_used` so the UI shows the chain.

**Q: How do the demo mode and LLM mode compare? Is demo just a stub?**
A: Same pipeline, different brain — that's the design. Both share one `ToolRegistry`; demo mode performs the *same computation* with rules (real slot extraction, real tool calls) instead of a model, so it produces complete, satisfying interactions offline and never crashes. The LLM path layers a JSON tool-calling protocol on top, with an honest fallback to demo mode if the model is unreachable.

**Q: What's the allowlist and why?**
A: `open_app` launches real macOS applications, so it accepts only names on a fixed allowlist (`calculator`, `notes`, `browser`, `mail`, …) — anything else gets a polite refusal listing what it *can* open. Same philosophy as the AST whitelist: deny-by-default is easier to reason about and to explain than trying to block every bad input.

## Ideas to extend it

- Add weather: a live `weather(city)` tool with a demo fallback that reads bundled city tables.
- Add a wake-word module to the frontend (mic on only after "Hey Orbit").
- Add *proactive memory*: a summarizer that periodically condenses old session turns into a durable note.
- Wire the ReAct loop to a multi-step plan: "book the demo and remind me Friday" → two chained tool calls.
- Add rate limiting and per-session token budgets for LLM mode, and surface both in the mode badge.

## Tests

```bash
cd 01-orbit-voice-assistant
../.venv/bin/python -m pytest -q        # 41 tests, all offline, ~0.2s
```

What they cover: every intent rule and the deliberate ordering (math beats greet, identity beats math lookalike); calculator safety (division by zero, huge exponents, `__import__` rejected) and traversal blocking on `read_file`; the `open_app` allowlist without ever launching an app; graceful offline `web_search`; notes-store persistence, corruption recovery, and delete-by-id/index/substring; session ring-buffer; and Flask end-to-end runs through the test client (frontend served, math answer, notes persisting across turns, empty-message handling).
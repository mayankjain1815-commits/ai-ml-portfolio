# 06. GH Activity Forge

> Generates a realistic-looking GitHub contribution year, then paints it as a hand-built green-square SVG.

> **⚠️ Read this first — the ethics live here.** This tool exists to render demo graphs, test contribution-graph UIs, and teach SVG/date math. Using it to fabricate a history you present as real engineering is dishonest, and it collapses instantly under review: the commits behind the squares are empty, the diffs are nothing, and anyone can run `git log`. The `fake_commits.sh` emitter is opt-in, loudly warned, and meant only for throwaway repos you never push. Green squares ≠ real engineering.

**Inspired by:** [shpota/github-activity-generator](https://github.com/shpota/github-activity-generator) — same idea (generate a year of activity and a script to backdate it), rebuilt from scratch here with deterministic profiles, a hand-written SVG renderer instead of a cloned image, tests, and an honest warning system instead of a silent default.

## What it does

- Generates one `(date, commit_count)` pair per day for a full year (`--year 2026`) or any custom range (`--from` / `--to`), with three profiles: `random`, `streak`, `custom`.
- Keeps it human: zero-commit days, quieter weekends, whole vacation weeks of blanks, and occasional 10+ burst days — all reproducible from a `--seed`.
- Renders GitHub's contribution graph **as SVG by hand**: 53 week-columns × 7 rows, 11 px rounded cells with 3 px gaps, GitHub's exact five-green palette, month labels, weekday labels, the "Less ▢▢▢▢▢ More" legend, per-cell tooltips, and a totals caption.
- Writes four artifacts: `contribution.svg`, `activity.json` (full structured data), `summary.md` (totals, busiest day, longest streak, per-month table), and an offline `report.html` that embeds the SVG in a dark GitHub-like page.
- Opt-in only: `--emit-git-script` additionally writes `fake_commits.sh`, which creates backdated `--allow-empty` commits via `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE` — with a warning header you have to scroll past before the first commit line.

## Quick start

```bash
cd 06-gh-activity-forge

# read the help first — it documents every flag
../.venv/bin/python -m gh_activity_forge --help

# the sample this README's numbers come from (writes ./out/)
../.venv/bin/python -m gh_activity_forge --year 2026 --profile random --seed 42 --output ./out

# other shapes that work
../.venv/bin/python -m gh_activity_forge --from 2026-03-01 --to 2026-08-31 --profile custom --output ./out
../.venv/bin/python -m gh_activity_forge --year 2024 --profile streak --seed 7 --output ./out

# the powerful opt-in (read the header of the file it writes!)
../.venv/bin/python -m gh_activity_forge --year 2026 --profile streak --seed 42 --emit-git-script --output ./out

# tests
../.venv/bin/python -m pytest -q
```

Then open `out/report.html` in a browser (works with the network off), or `out/contribution.svg` on its own. `out/` is gitignored — recreate it any time with the commands above.

## How it works

```
                    cli.py (argparse)
        --year | --from/--to   --profile   --seed   --output
                              │
                              ▼
   generator.py ── random.Random(seed) ──────────────────────┐
        │  list[DayActivity]                                │
        │  (date, commit_count) × 365, one per calendar day │
        │  realism: Poisson days, weekend dip,              │
        │  2 vacation weeks, 10+ bursts                     │
        ▼                                                   │
   ┌────────────┬──────────────┬───────────────┐            │
   ▼            ▼              ▼               ▼            │
 svg.py      report.py     report.py      git_script.py     │
 contribution activity.json  summary.md    fake_commits.sh   │
 .svg         report.html    (Markdown)    (opt-in only) ◄──┘
```

1. `cli.py` parses flags and turns `--year 2026` into the inclusive range `2026-01-01 .. 2026-12-31` (or validates your `--from`/`--to` pair; ranges over 5 years are rejected with an error).
2. `generator.py` seeds `random.Random(42)` and walks every day, asking the chosen profile for a count. The `random` profile draws Poisson-distributed commits (λ 1.8 weekdays / 0.8 weekends, ×6 on ~1% burst days); whole week-columns are pre-blanked as vacations.
3. You get back 365 `DayActivity` values — 564 commits over 258 active days for the sample command, busiest 2026-05-21 with 11, longest streak 13.
4. `svg.py` finds the Sunday on or before Jan 1 (2025-12-28), then computes each day's column (`days since that Sunday ÷ 7`) and row (`(weekday + 1) % 7`, Sunday-first like GitHub), picks a color bucket, and appends one escaped `<rect>` with a `<title>` tooltip. That's 365 cells across 53 columns in a 785 × 177 canvas.
5. `report.py` slices the SVG into `report.html`, aggregates totals and a per-month table into `activity.json` and `summary.md`.
6. Only if you passed `--emit-git-script`: `git_script.py` walks the same plan and emits one quoted `GIT_AUTHOR_DATE=... git commit --allow-empty` line per planned commit — under a 10-line warning header.

## Generate only vs. emit git script

This project has no API key and no network. The "two modes" are the safe default versus the powerful opt-in:

| | default: generate only | with `--emit-git-script` |
| --- | --- | --- |
| Files written | `contribution.svg`, `activity.json`, `summary.md`, `report.html` | + `fake_commits.sh` (executable) |
| Touches a git repo? | Never — pure file generation | Only if *you* later run the script inside one |
| Network needed | No | No |
| Warning system | Ethics note in README/report | Loud header inside the script itself, refuses to run outside a repo, never pushes anything |
| When to use | Mockups, dashboards, UI tests, learning SVG | Previewing a demo graph on a throwaway repo you will never present as real work |

## Project structure

```
06-gh-activity-forge/
├── README.md                     # this file
├── requirements.txt              # no runtime deps; pytest for the tests
├── .gitignore                    # out/, __pycache__, .pytest_cache, .env
├── conftest.py                   # keeps the package importable under plain pytest
├── gh_activity_forge/
│   ├── __init__.py               # package docstring + public exports
│   ├── __main__.py               # `python -m gh_activity_forge` entry point
│   ├── cli.py                    # argparse: dates, profile, seed, output, flags
│   ├── generator.py              # profiles -> list[DayActivity], date validation
│   ├── svg.py                    # hand-built GitHub-style SVG renderer
│   ├── report.py                 # activity.json, summary.md, report.html writers
│   └── git_script.py             # opt-in fake_commits.sh emitter (warned)
└── tests/
    ├── test_generator.py         # leap years, ranges, determinism, profiles
    ├── test_svg.py               # XML validity, alignment, palette, tooltips
    ├── test_report.py            # artifacts, JSON shape, offline HTML
    ├── test_git_script.py        # warnings, env vars, shell quoting, bash -n
    └── test_cli.py               # help text, end-to-end run, usage errors
```

## Explain it like I'm 19

Think of GitHub's contribution graph as a colouring-book calendar: 365 little squares, one per day, shaded from blank gray to dark green depending on how much you did. Plenty of us can draw the picture but not a real year's worth of events, so this project invents a believable year first — some busy weekdays, lazy weekends, two weeks off, a couple of heroic 11-commit days — and then colours the calendar in by numbers using GitHub's own five greens. Because the whole "year" is just a seeded list of numbers, the same seed always paints the exact same page, which is what makes it a demo and a test fixture rather than a slot machine. The deep end is the optional script: it can walk into a git repo and stamp out matching backdated commits, which is why it is buried behind a flag and starts with a warning instead of a "you're welcome". Use it to design a mockup, not to lie about your résumé.

## Explain it in an interview

**You use `datetime.date` everywhere — why not Unix timestamps? What are the date-math gotchas?**
A contribution graph is a calendar, not a set of instants: "March 3" only means something in a timezone, and a timestamp would silently shift days across midnight (a commit at 23:30 UTC is the *next* day in UTC+5:30). `date` has no time or zone, so the grid math is exact and testable. The three traps: leap years (`date(2024, 1, 1)..date(2024, 12, 31)` is 366 days, so I never hardcode 365); weekday alignment (`date.weekday()` is Monday=0 but GitHub's grid is Sunday-first, so row = `(weekday + 1) % 7`, and the first column must start on the Sunday *on or before* the range start or every square is off by one); and range edges (inclusive boundaries, `start > end` rejected rather than silently emptied).

**How do you generate the SVG? Why not matplotlib?**
I build the document as a list of escaped strings: one `<rect>` per day with an exact `x`/`y` from column/row math, a `<title>` child for the tooltip, plus caption, month labels, weekday labels and legend. `xml.sax.saxutils.escape` handles hostile text, and the tests parse the result with `xml.etree.ElementTree` to prove it is valid XML. Matplotlib is allowed but wrong for this: I want pixel-exact control of the 11 px cells and the tooltips, a ~65 KB file, no plotting dependency — and honestly, writing the geometry by hand is the point of the project.

**Why does seeded pseudorandomness matter?**
Same `(range, profile, seed)` must produce a bit-identical plan, so `--seed 42` is a reproducible artifact you can share, review, and snapshot. It also makes the tests honest: I can assert "the streak profile with seed 42 has a run of ≥5 consecutive active days" or "random seed 42 has a 10+ burst day and still has zero days" without mocking randomness. A seeded PRNG is deterministic, not cryptographic — which is exactly backwards from what you want for secrets, and exactly right for demos and tests.

**How do you make a fake year look real?**
Stack small realistic effects instead of one big distribution: weekday λ of 1.8 versus weekend 0.8 via Knuth's Poisson sampler, a ~1% chance of multiplying λ by 6 for burst days, and two whole pre-blanked week-columns that read as vacations. The `custom` profile adds a fixed weekly rhythm (weekdays 4–9, weekends 0–2) and the `streak` profile stamps a few 5–14 day streaks over a sparse background. The output is still data, so every rule is testable.

**Where is the ethical line between a demo graph and fake open-source contributions?**
A demo graph is labeled as such and used offline — a mockup, a UI test fixture, a teaching aid. Fake contributions are published to a repo or profile you present as your real work; the tell is trivial (empty commits, no diffs, uniform timestamps, machine-like bursts). That's why the graph files are the safe default and the git emitter is opt-in with a warning header, a repo check, and no push step. If a tool can be misused, the design job is to make the honest path the default and the dangerous path loud.

## Ideas to extend it

- Add a `--theme dark` flag that swaps in GitHub's dark palette and a dark `report.html` card.
- Import a real repo's history with `git log --pretty=%ad --date=short`, aggregate per day, and render *your actual* year instead of a generated one.
- Export a PNG (or a print-ready PDF) by wrapping the hand-written SVG, so the graph drops into slides and résumés.
- Add a `--compare` mode that renders two profiles side by side with a small stats table, useful for explaining the profiles visually.
- Add a stress/realism metric (`--report-metrics`) that scores a plan on zero-day ratio, burst count, and streak spread, then assert on it in tests.

## Tests

Run them from inside the project — no network, no API key, no sleeps:

```bash
cd 06-gh-activity-forge
../.venv/bin/python -m pytest -q
```

The suite has 25 tests across five files:

- `test_generator.py` — full-year coverage (2024 has Feb 29, 2025 does not), contiguous partial ranges, `start > end` and over-5-year and unknown-profile errors, determinism under a fixed seed, custom-profile weekend dip plus ≥7 blank vacation days, the streak profile's ≥5-day run, and burst/zero-day realism for `random`.
- `test_svg.py` — parses as valid XML, exactly 366/365 data cells for leap/non-leap years, 53 columns, every cell in the correct weekday row and week column, the five palette boundaries (`0→#ebedf0`, `1→#9be9a8`, `3→#40c463`, `6→#30a14e`, `12→#216e39`), GitHub-style tooltips, and caption/labels plus escaping of a hostile caption.
- `test_report.py` — all four artifacts, the opt-in fifth, cleanup of a stale generated `fake_commits.sh`, JSON range/totals/per-day shape, month aggregation, and an HTML report with inline SVG and no CDN or scripts.
- `test_git_script.py` — warning header, one backdated commit per planned count on the right days, executable bit, `bash -n` syntax validity, shell-quoting with apostrophes/`$HOME`, and seed determinism.
- `test_cli.py` — help contains every documented flag and the examples, an end-to-end run writes the files, `--quiet` prints nothing, and bad date ranges exit with code 2.


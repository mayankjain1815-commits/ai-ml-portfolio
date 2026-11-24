# Solar Atlas — landing page backend

A tiny, read-only Flask API behind the landing page's **solar system**:

- ten concept words are inner planets (`rag`, `agents`, … `iot`);
- 23 public repositories are outer planets across eight wider orbit bands;
- one deterministic star and 13 orbit bands tie the two classes together.

Click any planet on the page and the UI opens a detail panel with the record
*and* its orbital results. The service owns the records; `index.html` carries
the same JSON so the page still works with the server off, on a static host, or
from `file://`.

## Run it

```bash
cd backend
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m word_atlas          # http://127.0.0.1:5110
.venv/bin/python -m pytest -q           # 116 offline tests, no keys, no network
```

Port defaults to **5110** and can be changed with `PORT`. CORS is open because
the landing page is expected to work straight from `file://` as well as from a
static host.

## Endpoints

### Solar system

| Endpoint | What it returns |
|----------|-----------------|
| `GET /api/solar` | The star, all 33 planets, textures, stats and the honesty note. |
| `GET /api/solar/stats` | Body, moon, ring, band, star and period aggregates. |
| `GET /api/solar/<kind>/<slug>` | One planet's full record, orbital telemetry and neighbouring worlds. `kind` is `word` or `repo` (plural also accepted). |

Orbit radii, periods, inclinations, eccentricities, moon counts and rings are
**deterministic UI metadata derived from the slug**. They are reproducible and
shared by the canvas, API and embedded JSON; they are not astronomical facts.

### Concept words — inner planets

| Endpoint | What it returns |
|----------|-----------------|
| `GET /api/health` | Status, version, word/repo/body/theme counts and metadata snapshot. |
| `GET /api/words` | Summaries for all 10 words. `?q=`, `?category=`, `?limit=` supported. |
| `GET /api/words/<slug>` | Full record plus related words and the repos that use the word. |
| `GET /api/words/<slug>/related` | Words sharing a category or a project. |
| `GET /api/words/<slug>/repos` | Full repo records linked to that word. |
| `GET /api/categories` | Word category counts. |

### Repositories — outer planets

| Endpoint | What it returns |
|----------|-----------------|
| `GET /api/repos` | Repo summaries. `?q=`, `?language=`, `?category=`, `?word=`, `?sort=name|stars|updated|language`, `?limit=` supported. |
| `GET /api/repos/<slug>` | Full record: description, stack, highlights, linked words, related repos, canvas systems, clone command and GitHub URL. |
| `GET /api/repos/<slug>/related` | Repos sharing a category, word or canvas system. |
| `GET /api/languages` | Primary-language counts. |
| `GET /api/timeline` | Repos ordered by last-updated date. |

### Cross-cutting

| Endpoint | What it returns |
|----------|-----------------|
| `GET /api/search?q=` | Results from both planet classes, scored so prefix matches lead. |
| `GET /api/themes` | The remaining visual theme (`aurora`). |
| `GET /api/themes/<id>` | One theme's palette and flags. |
| `GET /api/stats` | Counts, stars, solar aggregates, palette and theme colours. |

Every word slug from the inner system works: `rag`, `agents`, `mlops`,
`forecast`, `signals`, `skills`, `risk`, `offline`, `demo`, `iot`. Every repo
slug from the outer system works too (`slop`, `omniroute`, `sih`, …). Unknown
slugs return JSON 404 with the list of valid slugs. All GitHub metadata is a
dated snapshot (`2026-11-24`) rather than a live call, so the service stays
offline and reproducible.

Examples:

```bash
curl -s http://127.0.0.1:5110/api/solar | python -m json.tool
curl -s http://127.0.0.1:5110/api/solar/words/rag | python -m json.tool
curl -s 'http://127.0.0.1:5110/api/repos?q=proxy&sort=stars'
curl -s 'http://127.0.0.1:5110/api/search?q=rag'
```

## Where the data lives

Four modules are the source of truth:

- `word_atlas/data.py` — the ten concept records (definition, pipeline, real
  code anchors, commands, interview answer, pitfalls, tests).
- `word_atlas/repos.py` — the 23 repository records, category colours, GitHub
  URLs, links back to concept words, and the 2026-11-24 metadata snapshot.
- `word_atlas/solar.py` — the star, the deterministic layout for all 33 worlds,
  neighbour computation and orbital aggregates.
- `word_atlas/themes.py` — the aurora palette. The festive skin was removed.

`index.html` embeds all four as JSON script tags. `python backend/sync_index.py`
refreshes them from the modules. Tests assert that the embedded objects equal
the API objects after parsing, that the catalog has a button for every slug,
and that every repo link and colour is grounded.

## Design notes

- **Read-only by design.** No database, no writes, no secrets; the service is
  safe to run locally beside any project.
- **Offline first.** The API has no outbound network calls, and CI runs its
  suite with no API keys.
- **Fallback in the client.** The UI renders the embedded copy synchronously,
  then upgrades to the API when the fetch succeeds. Search, stats and orbital
  data use the same pattern; a failed probe never removes visible content.
- **One model, two views.** Words link to repos, repos link back to words, and
  related records are computed from shared categories, words, projects or
  canvas systems rather than hand-maintained lists.
- **Layout as data.** Every visual orbit value is generated from the slug in
  Python, not guessed in JavaScript. The canvas and the API therefore show the
  same system, and the note in the payload says what the numbers mean.

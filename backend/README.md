# Word Atlas — landing page backend

A tiny, read-only Flask API behind the landing page's **two rotating 3D rings**:

- the outer ring holds the ten concept words (`rag`, `agents`, … `iot`);
- the inner, counter-rotating ring holds **23 public repositories** from the
  GitHub account, each with its own full detail record.

Click any word or repo on the page and the UI opens a detail panel. The service
owns the records; `index.html` carries the same JSON so the page still works
with the server off, on a static host, or from `file://`.

## Run it

```bash
cd backend
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m word_atlas          # http://127.0.0.1:5110
.venv/bin/python -m pytest -q           # 76 offline tests, no keys, no network
```

Port defaults to **5110** and can be changed with `PORT`. CORS is open because
the landing page is expected to work straight from `file://` as well as from a
static host.

## Endpoints

### Concept words — outer ring

| Endpoint | What it returns |
|----------|-----------------|
| `GET /api/health` | Status, version, word/repo/theme counts and metadata snapshot. |
| `GET /api/words` | Summaries for all 10 words. `?q=`, `?category=`, `?limit=` supported. |
| `GET /api/words/<slug>` | Full record plus related words and the repos that use the word. |
| `GET /api/words/<slug>/related` | Words sharing a category or a project. |
| `GET /api/words/<slug>/repos` | Full repo records linked to that word. |
| `GET /api/categories` | Word category counts. |

### Repositories — inner ring

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
| `GET /api/search?q=` | Results from both rings, scored so prefix matches lead. |
| `GET /api/themes` | Available visual themes (`aurora`, `christmas`). |
| `GET /api/themes/<id>` | One theme's palette, tagline and snow/ornament flags. |
| `GET /api/stats` | Counts, stars, palette and both themes' colours. |

Every word slug from the ring works: `rag`, `agents`, `mlops`, `forecast`,
`signals`, `skills`, `risk`, `offline`, `demo`, `iot`. Every repo slug from the
inner ring works too (`slop`, `omniroute`, `sih`, …). Unknown slugs return JSON
404 with the list of valid slugs. All metadata is a dated snapshot (`2026-11-24`)
rather than a live GitHub call, so the service stays offline and reproducible.

Examples:

```bash
curl -s http://127.0.0.1:5110/api/words/rag | python -m json.tool
curl -s 'http://127.0.0.1:5110/api/repos?q=proxy&sort=stars'
curl -s 'http://127.0.0.1:5110/api/search?q=rag'
curl -s http://127.0.0.1:5110/api/themes/christmas
```

## Where the data lives

Three modules are the source of truth:

- `word_atlas/data.py` — the ten concept records (definition, pipeline, real
  code anchors, commands, interview answer, pitfalls, tests).
- `word_atlas/repos.py` — the 23 repository records, category colours, GitHub
  URLs, links back to concept words, and the 2026-11-24 metadata snapshot.
- `word_atlas/themes.py` — the aurora and Christmas palettes. The Christmas
  theme recolours the three canvas systems and enables snow without changing
  their code.

`index.html` embeds all three as JSON script tags. Tests assert that the
embedded objects equal the API objects after parsing, that both HTML rings match
their modules slug-for-slug, and that every repo link and colour is grounded.

## Design notes

- **Read-only by design.** No database, no writes, no secrets; the service is
  safe to run locally beside any project.
- **Offline first.** The API has no outbound network calls, and CI runs its
  suite with no API keys.
- **Fallback in the client.** The UI renders the embedded copy synchronously,
  then upgrades to the API when the fetch succeeds. Search and stats use the
  same pattern; a failed probe never removes visible content.
- **Two rings, one model.** Repos point at concept words, words point back at
  repos, and related records are computed from shared categories, words,
  projects or canvas systems rather than hand-maintained lists.
- **Theme as data.** The Christmas skin is served by `/api/themes` and applied
  through CSS variables plus a canvas colour event; reduced-motion users get
  the palette without moving snow.

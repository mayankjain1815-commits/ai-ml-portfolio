# Word Atlas — landing page backend

A tiny, read-only Flask API that holds the **full explanation behind every word**
in the landing page's rotating 3D ring. Click a word on the page and the UI asks
this service for the details; if the service is not running, the page falls back
to the same records embedded in `index.html` so nothing breaks offline.

## Run it

```bash
cd backend
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m word_atlas          # http://127.0.0.1:5110
.venv/bin/python -m pytest -q           # 36 offline tests, no keys, no network
```

Port defaults to **5110** and can be changed with `PORT`. CORS is open because
the landing page is expected to work straight from `file://` as well as from a
static host.

## Endpoints

| Endpoint | What it returns |
|----------|-----------------|
| `GET /api/health` | Service status, version, word count. |
| `GET /api/words` | Summaries for all 10 words. `?q=`, `?category=`, `?limit=` supported. |
| `GET /api/words/<slug>` | Full record: definition, why it matters, pipeline steps, concepts, projects, real code anchors, commands, an interview answer, pitfalls, tests and related words. |
| `GET /api/words/<slug>/related` | Words sharing a category or a project. |
| `GET /api/categories` | Category counts. |
| `GET /api/stats` | Record counts and the aurora palette. |

Every slug from the ring works: `rag`, `agents`, `mlops`, `forecast`, `signals`,
`skills`, `risk`, `offline`, `demo`, `iot`. Unknown slugs return JSON 404 with
the list of valid slugs.

Example:

```bash
curl -s http://127.0.0.1:5110/api/words/rag | python -m json.tool
curl -s 'http://127.0.0.1:5110/api/words?q=sqlite&limit=2'
```

## Where the data lives

`word_atlas/data.py` is the single source of truth. Each of the ten records has
17 fields, including:

- `definition` and `why_it_matters`
- `how_it_works` — the pipeline, step by step
- `concepts`, `projects` and their role
- `code_anchors` — real repository files and symbols
- `commands` to reproduce the demo and the tests
- `interview_answer`, `pitfalls` and the relevant test files

The tests check that every anchor and README path actually exists, that all ten
slugs match the HTML ring, that colours come from the shared palette and that
related words are symmetric. So an explanation cannot quietly drift away from
the code it describes.

## Design notes

- **Read-only by design.** No database, no writes, no secrets; the service is
  safe to run locally beside any project.
- **Offline first.** The API has no outbound network calls, and CI runs its
  suite with no API keys.
- **Fallback in the client.** `index.html` carries the same ten records in a
  JSON script tag. The UI prefers the API and silently uses the embedded copy
  when the fetch fails, which keeps the standalone page fully functional.

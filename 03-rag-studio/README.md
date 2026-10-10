# 03. RAG Studio

> Retrieval-augmented generation built by hand, end to end: chunk, index, retrieve, answer, and *measure whether any of it helped*.

**Inspired by:** the original [RAG paper](https://arxiv.org/abs/2005.11401) (Lewis et al., 2020) and the "chat with your documents" tools it spawned (LlamaIndex, LangChain) — rebuilt here with no framework: the chunker, the TF-IDF vectorizer, cosine and MMR retrieval, the extractive generator, and the eval metrics are all small modules you can read, test, and defend line by line.

## What it does

- **`build`** — ingests `.md`, `.txt`, and `.pdf`, then chunks them with a boundary-aware word window and keeps full provenance (`02-dns-and-websites.md`, lines 1-11) for every chunk.
- **`ask` / `chat`** — retrieves the best chunks and answers with grounded `[n]` citations. Chat is an interactive REPL over the same index.
- **`eval`** — runs 15 labeled questions through the live pipeline and reports **recall@1/3/5, MRR, faithfulness, keyword coverage, and latency** to `evals/report.json`.
- **`demo`** — the whole story in one command: build, three questions, and the full eval table.
- Two interchangeable index modes behind one interface: hand-rolled **TF-IDF** (default, offline, deterministic) or **Gemini dense embeddings**, selected by whether a key is set.
- Query rewriting (thesaurus offline, Gemini online) and **MMR** diversity re-ranking (`--mmr`), both implemented by hand.

## Quick start

```bash
cd 03-rag-studio

# one command: build the index, answer three questions, run the full eval table
../.venv/bin/python -m rag_studio demo

# or step by step (--offline forces the deterministic paths even if a key is set)
../.venv/bin/python -m rag_studio build data/docs --offline
../.venv/bin/python -m rag_studio ask "why does the internet use packets?" --offline
../.venv/bin/python -m rag_studio eval --rebuild --offline

# interactive question/answer over the built index
../.venv/bin/python -m rag_studio chat

# tests (offline)
../.venv/bin/python -m pytest -q

# real LLM mode (optional)
cp .env.example .env   # then put your GEMINI_API_KEY in .env
```

The bundled `data/docs/` corpus is five short articles on how the internet works; `data/evals.json` is 15 labeled questions over them, one per answerable fact. `index/` and `evals/report.json` are generated artifacts and are gitignored — rebuild them any time with the commands above.

## How it works

```
  data/docs/*.md
        │
        ▼
 ┌─────────────┐   ┌──────────────┐   ┌───────────────┐
 │   ingest    │──▶│   chunker    │──▶│     index     │
 │ text+spans  │   │ word windows │   │ TF-IDF / gem  │
 │ offset→line │   │ cut on .!?¶  │   │  L2-normalized│
 └─────────────┘   └──────────────┘   └───────────────┘
                                              │
        question                              ▼
           │                          ┌───────────────┐
           ▼                          │   retriever   │
 ┌─────────────┐                     │ rewrite+cosine│
 │ expand_query│────────────────────▶│  top-k / MMR  │
 │ thesaurus / │                     └───────────────┘
 │   Gemini    │                             │
 └─────────────┘                             ▼
                                    ┌───────────────┐
                                    │   generate    │
                                    │ extractive /  │
                                    │    Gemini     │
                                    └───────────────┘
                                            │
                                            ▼
                                   answer + [n] citations
                                            │
                                            ▼
                                    ┌───────────────┐
                                    │     evals     │
                                    │ recall/MRR/   │
                                    │ faithfulness  │
                                    └───────────────┘
```

One full run, tracing the demo question *"How does DNS turn a domain name into an IP address?"*:

1. **ingest** — `load_directory("data/docs")` reads the five files and, for each, builds a span map from character offset back to a 1-based line number.
2. **chunk** — `chunk_documents` cuts each file into ≤400-word windows (80-word overlap), but scores candidate cuts inside a search band and takes the best: paragraph break > sentence end > line end > heavily-penalized mid-sentence. Result: 10 chunks, each with a label like `lines 1-11`.
3. **index** — every chunk is tokenized (case-fold, strip accents, drop stopwords, crude singularize), smoothed idf `ln((1+N)/(1+df)) + 1` is computed, the `(10 × 722)` matrix is filled with `tf × idf` and L2-normalized, then saved as `index/meta.json` + `index/vectors.npz`.
4. **rewrite** — `expand_query` adds variants. Offline that's a small thesaurus (`dns` → `resolver`, `lookup`); with a key it's three Gemini paraphrases, with the thesaurus as fallback.
5. **score** — each variant is embedded into the same vocabulary space and every chunk is scored by cosine similarity. Because rows are already unit length, cosine is just a dot product. Scores merge by max across variants and non-positive matches are dropped.
6. **generate** — `_extractive_answer` scores each sentence of each retrieved chunk by `(query-term overlap) × (chunk cosine score)`, stitches the best 2-4 together, and appends `[n]` citations pointing at the retrieval order. Sentences are copied verbatim, so the answer is grounded by construction.
7. **evaluate** — `run_evaluation` repeats 1-6 for all 15 questions, finds the rank of each question's gold source, and writes recall@{1,3,5}, MRR, faithfulness, keyword coverage, and latency to `evals/report.json`.

On the bundled corpus and default tokenizer this scores **recall@1 0.93, recall@3 1.00, recall@5 1.00, MRR 0.97, faithfulness 1.00, keyword coverage 0.71** at ~1.9 ms per question — a real baseline you can then beat.

## Demo mode vs. real mode

| Stage | No API key (demo) | With `GEMINI_API_KEY` |
|---|---|---|
| Query rewriting | thesaurus synonyms appended (`thesaurus.py`) | model returns 3 paraphrases; thesaurus on failure |
| Index / embeddings | hand-rolled TF-IDF (`tfidf` mode) | `text-embedding-004` dense vectors (`gemini` mode) |
| Answer generation | extractive: best sentences copied verbatim with `[n]` citations | Gemini writes 2-4 cited sentences, then `verify_citations` drops any out-of-range `[n]` |
| Failure handling | n/a — deterministic offline | any Gemini error falls back to the extractive path, so a flaky network never errors the user out |
| Metrics | identical — the eval harness scores whatever pipeline ran | identical |

Every command above works with no key. Copy `.env.example` to `.env`, add `GEMINI_API_KEY`, and the same commands upgrade in place; `--offline` pins demo mode even when a key is present.

## Project structure

```
03-rag-studio/
├── rag_studio/                  # the Python package
│   ├── ingest.py                # .txt/.md/.pdf loading + offset→line/page span maps
│   ├── chunker.py               # boundary-aware word-window chunking with provenance
│   ├── text.py                  # the one tokenizer and sentence splitter everything shares
│   ├── thesaurus.py             # offline query expansion table
│   ├── index.py                 # hand-rolled TF-IDF, cosine, save/load; Gemini mode
│   ├── retriever.py             # query rewrite, top-k, thresholding, hand-written MMR
│   ├── generate.py              # extractive (demo) and Gemini (real) answers + citation check
│   ├── llm.py                   # Gemini REST client with retries and an offline generator
│   ├── evals/
│   │   ├── metrics.py           # recall@k, MRR, faithfulness, keyword coverage (by hand)
│   │   └── harness.py           # runs the labeled set, builds the ASCII report
│   └── cli.py                   # build / load / ask / chat / eval / demo
├── data/
│   ├── docs/                    # 5 bundled articles (the retrieval corpus)
│   └── evals.json               # 15 labeled questions with gold sources + keywords
├── index/                       # generated: meta.json + vectors.npz (gitignored)
└── tests/                       # 68 tests across 7 files, all offline
```

## Explain it like I'm 19

Imagine a library with no librarian and no card catalog. You walk in, shout a
question, and every book would have to answer — useless. RAG Studio first builds
a card catalog: it reads every page, breaks it into note-sized pieces, and for
each word records which notes use it. A question becomes a set of words, the
catalog points at the notes that share those words, and the best notes are taped
together into an answer with a footnote on each sentence pointing back at its
page. The clever part is the last step: it runs 15 test questions with known
answers and prints a scorecard, so you can tell a better catalog from a worse one
instead of guessing.

## Explain it in an interview

**Q: Why build retrieval yourself instead of using a vector database or LangChain?**
A: Two reasons. First, the thing I'm being evaluated on is the *math and the
failure modes*, and those are invisible behind a library call — I can show you
the idf formula, the MMR objective, and the exact place a query with no known
terms scores zero. Second, the interface is deliberately one object
(`TfidfIndex`), so swapping in a real vector store is an implementation change,
not a rewrite. Building the baseline is how I earned the right to replace it.

**Q: How do you know RAG is actually working?**
A: The eval harness separates the two ways RAG fails. Retrieval can miss the
right document — measured by recall@k and MRR — and generation can say things
the sources never said — measured by faithfulness (the share of the answer's
content words present in the retrieved chunks) and keyword coverage. On the
bundled corpus I get recall@3 1.00 and faithfulness 1.00, which is suspiciously
clean precisely because demo mode copies sentences verbatim; that's the point of
a controlled baseline. Metrics first, tweaks second.

**Q: What's the hardest part of chunking, and how did you handle it?**
A: A blind fixed-size window slices sentences in half, which produces fragment
answers and ugly citations. So I make the cut *choose*: near the target word
count I score every candidate cut and prefer a paragraph break, then a sentence
end, then a line end, penalizing mid-sentence cuts and breaking ties by distance
from the target. Overlap exists because a fact straddling a cut must be whole in
at least one chunk, and a remainder smaller than the overlap is absorbed rather
than emitted as a near-duplicate tail.

**Q: How does demo mode stay honest rather than a stub?**
A: It's a parallel implementation of the same pipeline. Retrieval is the real
TF-IDF index with the real cosine math; only two stages differ — query rewriting
uses a thesaurus instead of a model, and generation extracts the best-matching
sentences verbatim instead of asking Gemini. Everything upstream and downstream
is identical, so the eval numbers describe the real system, not a toy branch.

**Q: Why implement MMR by hand?**
A: Because the objective is three lines and the trade-off is the interesting
part: `λ·relevance − (1−λ)·max_similarity_to_already_picked`. Watching λ go from
1.0 (pure relevance, identical to top-k) to 0.0 (pure diversity) makes the
precision/coverage trade-off concrete instead of a magic setting in a library.
It also gave me a clean unit test: at λ=1 MMR must exactly reproduce plain top-k.

## Ideas to extend it

- Add a real vector store (FAISS or a numpy IVF index) behind the same `TfidfIndex` interface and re-run the eval to compare recall.
- Add hybrid retrieval: blend BM25/TF-IDF lexical scores with dense scores and tune the mix against the existing 15-question set.
- Add a cross-encoder-style re-ranker over the top 20 hits and report the recall@1 delta.
- Expand the corpus to PDFs (the loader already supports them) and watch provenance labels switch from "lines" to "pages".
- Turn the eval harness into a CI gate: fail the build if recall@3 drops below a committed threshold.

## Tests

```bash
cd 03-rag-studio
../.venv/bin/python -m pytest -q     # 68 tests, fully offline
```

Seven files cover: the tokenizer's folding/singularizing rules and sentence
splitting (`test_text.py`), chunk boundary scoring, overlap, and validation
(`test_chunker.py`), TF-IDF math, save/load round-trips, MMR, and the
bundled-corpus integration (`test_retrieval.py`), extractive answers and
citation verification (`test_generate.py`), the metrics and the end-to-end eval
harness (`test_evals.py`), thesaurus expansion and the offline LLM fallback
(`test_thesaurus_llm.py`), and every CLI subcommand into `tmp_path`
(`test_cli.py`). An autouse fixture deletes the API-key environment variables, so
no test can accidentally make a real network call.

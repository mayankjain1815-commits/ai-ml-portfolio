"""Command-line interface: build, load, ask, chat, eval, and demo.

Plain ASCII output on purpose (no colour libraries). Every command resolves the
same way: reuse the index on disk when it exists, build it from the docs folder
when it does not, and let ``--offline`` force the deterministic demo paths even
if a Gemini key happens to be set.

    python -m rag_studio build data/docs
    python -m rag_studio ask "why does the internet use packets?"
    python -m rag_studio chat
    python -m rag_studio eval --rebuild
    python -m rag_studio demo
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from time import perf_counter

from rag_studio import __version__, llm
from rag_studio.chunker import DEFAULT_OVERLAP, DEFAULT_WINDOW, chunk_documents
from rag_studio.evals.harness import format_report, load_questions, run_evaluation
from rag_studio.generate import Answer, answer as answer_question
from rag_studio.index import TfidfIndex, build_index, load_index, save_index
from rag_studio.ingest import load_directory

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOCS = PROJECT_ROOT / "data" / "docs"
DEFAULT_INDEX = PROJECT_ROOT / "index"
DEFAULT_REPORT = PROJECT_ROOT / "evals" / "report.json"

DEMO_QUESTIONS = (
    "How does DNS turn a domain name into an IP address?",
    "Why does the internet split data into packets?",
    "How do HTTPS certificates prove a website is who it says it is?",
)

_RULE_WIDTH = 66


# -- small output helpers --------------------------------------------------


def _banner(title: str) -> None:
    line = f"=== {title} " + "=" * max(0, _RULE_WIDTH - len(title) - 5)
    print(f"\n{line}")


def _print_sources(answer: Answer) -> None:
    if not answer.hits:
        print("  (no sources matched)")
        return
    print("  sources:")
    for rank, hit in enumerate(answer.hits, start=1):
        print(f"    [{rank}] {hit.score:.3f}  {hit.chunk.source} ({hit.chunk.position})")


def _print_answer(question: str, answer: Answer, *, show_sources: bool = True) -> None:
    print(f"  Q: {question}")
    print(f"  A: {answer.text}")
    if show_sources:
        _print_sources(answer)
    mode = "extractive (demo)" if answer.mode == "extractive" else "gemini (real)"
    print(
        f"  mode: {mode} | {answer.latency_ms:.1f} ms | "
        f"{len(answer.queries)} query variant(s)"
    )


# -- mode / index plumbing -------------------------------------------------


def _offline(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "offline", False))


def _api_key(args: argparse.Namespace) -> str | None:
    """None means "auto-detect"; empty string means "force demo mode"."""
    return "" if _offline(args) else None


def _embedding_mode(args: argparse.Namespace) -> str:
    if not _offline(args) and llm.get_api_key():
        return "gemini"
    return "tfidf"


def _build(args: argparse.Namespace) -> TfidfIndex:
    """Ingest + chunk + index the docs folder, writing to the index directory."""
    docs_dir = Path(getattr(args, "docs", DEFAULT_DOCS))
    index_dir = Path(getattr(args, "index", DEFAULT_INDEX))
    window = getattr(args, "window", DEFAULT_WINDOW)
    overlap = getattr(args, "overlap", DEFAULT_OVERLAP)

    started = perf_counter()
    documents = load_directory(docs_dir)
    if not documents:
        raise SystemExit(f"no supported documents found in {docs_dir}")
    chunks = chunk_documents(documents, window=window, overlap=overlap)
    mode = _embedding_mode(args)
    index = build_index(chunks, mode=mode)
    save_index(index, index_dir)
    elapsed_ms = (perf_counter() - started) * 1000.0

    _banner(f"build: {docs_dir}")
    for document in documents:
        count = sum(1 for chunk in chunks if chunk.source == document.source)
        print(f"  {document.source:<36} {count:>3} chunk(s)")
    print(
        f"  index: {len(chunks)} chunks, {mode} mode"
        + (f", {len(index.vocabulary)} terms" if mode == "tfidf" else "")
    )
    print(f"  saved to {index_dir} (meta.json + vectors.npz) in {elapsed_ms:.1f} ms")
    return index


def _load_or_build(args: argparse.Namespace, *, rebuild: bool = False) -> TfidfIndex:
    index_dir = Path(getattr(args, "index", DEFAULT_INDEX))
    if not rebuild and (index_dir / "meta.json").is_file():
        return load_index(index_dir)
    print(f"  no usable index at {index_dir} - building one first")
    return _build(args)


# -- commands --------------------------------------------------------------


def _cmd_build(args: argparse.Namespace) -> int:
    llm.log_demo_mode_once()
    _build(args)
    return 0


def _cmd_load(args: argparse.Namespace) -> int:
    index_dir = Path(args.index)
    started = perf_counter()
    index = load_index(index_dir)
    elapsed_ms = (perf_counter() - started) * 1000.0
    _banner(f"load: {index_dir}")
    print(f"  chunks:     {len(index.chunks)}")
    print(f"  sources:    {len({chunk.source for chunk in index.chunks})}")
    print(f"  mode:       {index.mode}")
    if index.mode == "tfidf":
        print(f"  vocabulary: {len(index.vocabulary)} terms")
    print(f"  created:    {index.created_at}")
    print(f"  loaded in {elapsed_ms:.1f} ms")
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    llm.log_demo_mode_once()
    index = _load_or_build(args)
    result = answer_question(
        index,
        args.question,
        k=args.k,
        min_score=args.min_score,
        mmr=args.mmr,
        api_key=_api_key(args),
    )
    _banner("ask")
    _print_answer(args.question, result)
    return 0


def _cmd_chat(args: argparse.Namespace) -> int:
    llm.log_demo_mode_once()
    index = _load_or_build(args)
    mode = "demo (offline)" if _api_key(args) == "" else ("real" if llm.get_api_key() else "demo")
    _banner("chat")
    print(f"  RAG Studio chat over {len(index.chunks)} chunks ({mode} mode).")
    print("  /sources shows the last answer's citations, /help lists commands, /exit quits.")

    last: Answer | None = None
    while True:
        try:
            line = input("\nask> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return 0
        if not line:
            continue
        if line in ("/exit", "/quit"):
            print("bye")
            return 0
        if line == "/help":
            print("  /sources  show citations for the last answer")
            print("  /exit     leave the chat")
            print("  anything else is a question")
            continue
        if line == "/sources":
            if last is None:
                print("  ask a question first")
            else:
                _print_sources(last)
            continue
        last = answer_question(
            index,
            line,
            k=args.k,
            min_score=args.min_score,
            mmr=args.mmr,
            api_key=_api_key(args),
        )
        print(f"  A: {last.text}")


def _cmd_eval(args: argparse.Namespace) -> int:
    llm.log_demo_mode_once()
    index = _load_or_build(args, rebuild=args.rebuild)
    questions = load_questions()
    report = run_evaluation(
        index,
        questions,
        ks=tuple(args.k),
        api_key=_api_key(args),
        report_path=args.report,
    )
    _banner(f"eval: {len(questions)} questions, k={','.join(map(str, args.k))}")
    print(format_report(report))
    print(f"\n  report -> {Path(args.report)}")
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    llm.log_demo_mode_once()
    _banner("demo: bundled docs end to end")
    index = _build(args)

    _banner("demo: three questions")
    for question in DEMO_QUESTIONS:
        result = answer_question(
            index, question, k=args.k, min_score=0.0, mmr=False, api_key=_api_key(args)
        )
        _print_answer(question, result)

    _banner("demo: evaluation")
    report = run_evaluation(
        index,
        load_questions(),
        ks=(1, 3, 5),
        api_key=_api_key(args),
        report_path=args.report,
    )
    print(format_report(report))
    print(f"\n  report -> {Path(args.report)}")
    print("\n  demo complete: index/ and evals/report.json are on disk.")
    return 0


# -- parser ----------------------------------------------------------------


def _parse_ks(raw: str) -> list[int]:
    try:
        values = sorted({int(part) for part in raw.split(",") if part.strip()})
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected comma-separated integers, got {raw!r}") from exc
    if not values or values[0] < 1:
        raise argparse.ArgumentTypeError("k values must be positive integers")
    return values


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m rag_studio",
        description="RAG Studio - chat with your documents (build, ask, chat, eval, demo).",
    )
    parser.add_argument("--version", action="version", version=f"rag-studio {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--index", default=str(DEFAULT_INDEX), help="index directory")
        p.add_argument("--docs", default=str(DEFAULT_DOCS), help="documents directory")
        p.add_argument("--offline", action="store_true", help="force deterministic demo mode")

    build = sub.add_parser("build", help="ingest and index a documents directory")
    build.add_argument("docs_positional", nargs="?", default=None, help=argparse.SUPPRESS)
    build.add_argument("--window", type=int, default=DEFAULT_WINDOW, help="words per chunk")
    build.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP, help="overlap in words")
    common(build)
    build.set_defaults(func=_cmd_build)

    load = sub.add_parser("load", help="load an index and print its stats")
    load.add_argument("--index", default=str(DEFAULT_INDEX), help="index directory")
    load.set_defaults(func=_cmd_load)

    ask = sub.add_parser("ask", help="answer one question")
    ask.add_argument("question")
    ask.add_argument("--k", type=int, default=5, help="chunks to retrieve")
    ask.add_argument("--min-score", type=float, default=0.0, help="cosine score floor")
    ask.add_argument("--mmr", action="store_true", help="diversify hits with MMR")
    common(ask)
    ask.set_defaults(func=_cmd_ask)

    chat = sub.add_parser("chat", help="interactive REPL over the index")
    chat.add_argument("--k", type=int, default=5, help="chunks to retrieve")
    chat.add_argument("--min-score", type=float, default=0.0, help="cosine score floor")
    chat.add_argument("--mmr", action="store_true", help="diversify hits with MMR")
    common(chat)
    chat.set_defaults(func=_cmd_chat)

    ev = sub.add_parser("eval", help="run the eval harness")
    ev.add_argument("--k", type=_parse_ks, default=[1, 3, 5], help="k sweep, e.g. 1,3,5")
    ev.add_argument("--rebuild", action="store_true", help="rebuild the index first")
    ev.add_argument("--report", default=str(DEFAULT_REPORT), help="report output path")
    common(ev)
    ev.set_defaults(func=_cmd_eval)

    demo = sub.add_parser("demo", help="build, ask three questions, and run the evals")
    demo.add_argument("--k", type=int, default=5, help="chunks to retrieve")
    demo.add_argument("--report", default=str(DEFAULT_REPORT), help="report output path")
    demo.add_argument("--window", type=int, default=DEFAULT_WINDOW, help="words per chunk")
    demo.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP, help="overlap in words")
    common(demo)
    demo.set_defaults(func=_cmd_demo)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch; returns a process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "docs_positional", None):
        args.docs = args.docs_positional
    return int(args.func(args))

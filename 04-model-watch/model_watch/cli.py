"""Command-line entry point for Model Watch.

    python -m model_watch train                 # generate → train → register
    python -m model_watch simulate [--days N]   # replay the stream through the monitor
    python -m model_watch dashboard             # Flask UI on http://127.0.0.1:5104
    python -m model_watch report                # plain-text summary of the latest run
    python -m model_watch demo                  # train → simulate → report (quick start)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from model_watch.dashboard import serve as dashboard_serve
from model_watch.monitor import run_monitoring, render_report
from model_watch.registry import ModelRegistry
from model_watch.train import reference_frame, train

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = PROJECT_ROOT / "registry"
DEFAULT_RUNS = PROJECT_ROOT / "runs" / "latest"

logger = logging.getLogger("model_watch")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="model_watch",
        description="MLOps monitoring for a churn model: train, simulate a "
        "production stream, detect drift, alert, and visualize.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("train", help="generate data, train two models, register the winner")
    sub.add_parser("report", help="print a plain-text summary of the latest monitoring run")
    sub.add_parser("dashboard", help="start the Flask dashboard on port 5104")

    sim = sub.add_parser("simulate", help="replay the production stream through the monitor")
    sim.add_argument("--days", type=int, default=60, help="simulated days (default 60)")
    sim.add_argument("--batch-size", type=int, default=200, help="rows per day (default 200)")
    sim.add_argument("--seed", type=int, default=7, help="stream seed (default 7)")
    sim.add_argument("--out", type=str, default=None, help="run output dir (default runs/latest)")

    demo = sub.add_parser("demo", help="run train → simulate → report end-to-end")
    demo.add_argument("--days", type=int, default=60, help="simulated days (default 60)")

    for p in (parser, sub.choices["train"], sub.choices["simulate"], sub.choices["demo"]):
        p.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    return parser


def _register_new_model(registry: ModelRegistry, result: "TrainResult") -> int:
    return registry.register(
        model=result.model,
        algorithm=result.algorithm,
        hyperparams=result.hyperparams,
        metrics=result.metrics,
        dataset_hash=result.dataset_hash,
        feature_names=result.feature_names,
        dataset_seed=result.dataset_seed,
        n_rows=result.n_rows,
        notes="churn model from seeded synthetic data",
    )


def cmd_train(args: argparse.Namespace, registry: ModelRegistry) -> None:
    result = train(seed=42)
    version = _register_new_model(registry, result)
    print(f"registered model_v{version}.pkl ({result.algorithm})")
    for name in ("logistic_regression", "random_forest"):
        m = result.candidate_metrics[name]
        print(f"  {name:<19} acc={m['accuracy']:.3f} f1={m['f1']:.3f} auc={m['roc_auc']:.3f}")
    print(f"  winner by ROC-AUC: {result.algorithm} (auc={result.auc:.3f})")


def cmd_simulate(args: argparse.Namespace, registry: ModelRegistry) -> None:
    model, manifest = registry.load()
    seed = manifest.get("dataset_seed") or 42
    n_rows = manifest.get("n_rows") or 12_000
    out_dir = Path(args.out) if args.out else DEFAULT_RUNS
    summary = run_monitoring(
        model=model,
        manifest=manifest,
        reference=reference_frame(seed=seed, n_rows=n_rows),
        days=args.days,
        batch_size=args.batch_size,
        seed=args.seed,
        out_dir=out_dir,
    )
    print(f"monitored {summary['days']} days → {out_dir}")
    alerts = summary.get("alert_summary") or {}
    worst = max(
        (s["severity"] for s in (summary.get("features") or {}).values()),
        default="ok",
    )
    print(f"worst feature-drift severity: {worst}")
    print(f"alerts: {alerts.get('alert', 0)} · warnings: {alerts.get('warn', 0)}")


def cmd_report(_args: argparse.Namespace, _registry: ModelRegistry) -> None:
    json_path = DEFAULT_RUNS / "monitor.json"
    if not json_path.exists():
        sys.exit("no run found — run `python -m model_watch simulate` (or `demo`) first")
    import json

    summary = json.loads(json_path.read_text(encoding="utf-8"))
    print(render_report(summary))


def cmd_dashboard(_args: argparse.Namespace, _registry: ModelRegistry) -> None:
    print("dashboard → http://127.0.0.1:5104  (Ctrl-C to stop)")
    dashboard_serve()


def cmd_demo(args: argparse.Namespace, registry: ModelRegistry) -> None:
    print("[1/3] training + registering model ...")
    result = train(seed=42)
    version = _register_new_model(registry, result)
    print(f"      registered model_v{version}.pkl ({result.algorithm}, auc={result.auc:.3f})")

    print("[2/3] replaying 60 days of production traffic through the monitor ...")
    model, manifest = registry.load()
    summary = run_monitoring(
        model=model,
        manifest=manifest,
        reference=reference_frame(seed=result.dataset_seed, n_rows=result.n_rows),
        days=args.days,
        out_dir=DEFAULT_RUNS,
    )
    print(f"      monitored {summary['days']} days → runs/latest/")

    print("[3/3] monitoring report\n")
    print(render_report(summary))
    print("\ndashboard:  python -m model_watch dashboard  →  http://127.0.0.1:5104")


def main(argv: list[str] | None = None) -> int:
    parser = _make_parser()
    args = parser.parse_args(argv)
    _configure_logging(verbose=getattr(args, "verbose", False))
    registry = ModelRegistry(DEFAULT_REGISTRY)

    handlers = {
        "train": cmd_train,
        "simulate": cmd_simulate,
        "report": cmd_report,
        "dashboard": cmd_dashboard,
        "demo": cmd_demo,
    }
    try:
        handlers[args.command](args, registry)
    except Exception as exc:  # surface cleanly for a CLI audience
        logger.exception("%s failed", args.command)
        sys.exit(f"error: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
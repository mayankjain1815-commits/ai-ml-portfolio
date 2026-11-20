"""Command-line entry point for Disaster Watch."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .config import DEFAULT_RUNS
from .dashboard import serve as dashboard_serve
from .forecast_gen import generate_forecast
from .monitor import run_monitoring

logger = logging.getLogger("disaster_watch")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="disaster_watch",
        description="Forecast-driven disaster monitoring: weather → risk → alerts → dashboard",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("forecast", help="generate forecast data only")
    sub.add_parser("report", help="print summary of latest run")
    sub.add_parser("dashboard", help="start authority dashboard on port 5107")

    sim = sub.add_parser("simulate", help="run full pipeline")
    sim.add_argument("--hours", type=int, default=72)
    sim.add_argument("--seed", type=int, default=13)

    demo = sub.add_parser("demo", help="generate forecast → assess risk → alerts → incidents")
    demo.add_argument("--hours", type=int, default=72)
    demo_india = sub.add_parser("demo-india", help="India-wide Sanket console")
    demo_india.add_argument("--hours", type=int, default=120)

    for p in (parser, sub.choices["forecast"], sub.choices["simulate"], sub.choices["demo"], sub.choices["demo-india"]):
        p.add_argument("-v", "--verbose", action="store_true")
    return parser


def cmd_forecast(args: argparse.Namespace) -> None:
    forecast = generate_forecast(seed=13, hours=72)
    print(f"generated {len(forecast)} forecast rows (6 areas × 72 hours)")
    print(f"sample: {forecast[0]['area_name']} @ {forecast[0]['timestamp']} rain={forecast[0]['rain_mm_h']}mm/h")


def cmd_simulate(args: argparse.Namespace) -> None:
    summary = run_monitoring(hours=args.hours, seed=args.seed)
    print(f"monitored {len(summary['current_weather'])} areas over {summary['hours']} hours")
    print(f"active alerts: {summary['alert_count']}")
    print(f"affected areas: {summary['affected_count']}")


def cmd_report(_args: argparse.Namespace) -> None:
    path = DEFAULT_RUNS / "monitor.json"
    if not path.exists():
        sys.exit("no run found — run `python -m disaster_watch demo` first")
    summary = json.loads(path.read_text(encoding="utf-8"))
    print("=" * 60)
    print("DISASTER WATCH - AUTHORITY REPORT")
    print("=" * 60)
    print(f"Generated: {summary.get('generated_at')}")
    print(f"Areas monitored: {len(summary.get('current_weather') or [])}")
    print(f"Active alerts: {summary.get('alert_count')}")
    print(f"Affected areas: {summary.get('affected_count')}")
    print("\nCURRENT WEATHER:")
    for cw in summary.get("current_weather") or []:
        name = cw.get('district_name') or cw.get('area_name') or cw.get('district_id')
        print(f"  {name}: {cw['rain_mm_h']}mm/h, {cw['temperature_c']}°C, {cw['humidity_pct']}% humidity, {cw['wind_kph']}kph wind, risk={cw['risk_level']} ({cw['risk_index']})")
    print("\nACTIVE ALERTS:")
    for a in summary.get("active_alerts") or []:
        print(f"  [{a['severity'].upper()}] {a['alert_type']}: {a['location']} - {a['message']}")
    if not summary.get("active_alerts"):
        print("  None")
    print("\nAFFECTED AREAS:")
    for af in summary.get("affected_areas") or []:
        print(f"  {af['area_name']}: {af['primary_threat']}, pop~{af['population_exposure']}, radius {af['impact_radius_km']}km")
    if not summary.get("affected_areas"):
        print("  None")
    print("\nRECENT INCIDENTS (top 5):")
    for inc in (summary.get("recent_incidents") or [])[:5]:
        print(f"  [{inc['type']}] {inc['location']}: {inc['description']}")
    print("=" * 60)


def cmd_dashboard(_args: argparse.Namespace) -> None:
    print("Disaster Watch Authority Dashboard → http://127.0.0.1:5107  (Ctrl-C to stop)")
    dashboard_serve()


def cmd_demo(args: argparse.Namespace) -> None:
    print("[1/4] Generating forecast data...")
    forecast = generate_forecast(seed=13, hours=args.hours)
    print(f"      {len(forecast)} rows for 6 areas")

    print("[2/4] Computing disaster risk levels...")
    from .risk_model import score_forecast
    scored = score_forecast(forecast)
    high_risk = [s for s in scored if s["risk_level"] in ("high", "critical")]
    print(f"      {len(high_risk)} high/critical risk readings")

    print("[3/4] Issuing alerts and identifying affected areas...")
    summary = run_monitoring(hours=args.hours, seed=13)
    print(f"      {summary['alert_count']} active alerts, {summary['affected_count']} affected areas")

    print("[4/4] Building incident log...")
    print(f"      {len(summary['recent_incidents'])} recent incidents logged")

    print("\n" + "=" * 50)
    print(f"Alerts: {summary['alert_count']} | Affected: {summary['affected_count']}")
    print("=" * 50)
    print("\nDashboard: python -m disaster_watch dashboard → http://127.0.0.1:5107")


def main(argv: list[str] | None = None) -> int:
    parser = _make_parser()
    args = parser.parse_args(argv)
    _configure_logging(verbose=getattr(args, "verbose", False))
    handlers = {
        "forecast": cmd_forecast,
        "simulate": cmd_simulate,
        "report": cmd_report,
        "dashboard": cmd_dashboard,
        "demo": cmd_demo,
        "demo-india": cmd_demo_india,
    }
    try:
        handlers[args.command](args)
    except Exception as exc:
        logger.exception("%s failed", args.command)
        sys.exit(f"error: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


from .monitor_india import run_monitoring_india


def cmd_demo_india(args: argparse.Namespace) -> None:
    print("[1/4] Generating India-wide forecast (120h)...")
    summary = run_monitoring_india(hours=args.hours, seed=2026)
    print(f"      {summary['areas_monitored']} districts monitored")
    print("[2/4] Computing risk levels...")
    print(f"      {summary['affected_count']} districts flagged")
    print("[3/4] Issuing alerts...")
    print(f"      {summary['alert_count']} active alerts")
    print("[4/4] Building incident log...")
    print(f"      {len(summary['recent_incidents'])} incidents")
    print("\nSanket India Dashboard: python -m disaster_watch dashboard → http://127.0.0.1:5107")


# Add to parser

"""Monitor orchestrator — runs forecast -> risk -> alerts -> incidents. Builds the full picture for the dashboard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .alert_engine import AlertEngine
from .config import DEFAULT_RUNS
from .forecast_gen import generate_forecast
from .incident_log import IncidentLog
from .risk_model import score_forecast


def run_monitoring(
    hours: int = 72,
    seed: int = 13,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """Run full monitoring pipeline and save outputs."""
    out_dir = out_dir or DEFAULT_RUNS
    out_dir.mkdir(parents=True, exist_ok=True)

    forecast = generate_forecast(seed=seed, hours=hours)
    scored = score_forecast(forecast)
    alerts = AlertEngine().issue_alerts(scored)
    incidents = IncidentLog().build_incidents(alerts, scored)

    by_area: dict[str, dict[str, Any]] = {}
    for row in scored:
        aid = row["area_id"]
        if aid not in by_area or row["timestamp"] > by_area[aid]["timestamp"]:
            by_area[aid] = row
    current_weather = list(by_area.values())

    affected = []
    affected_ids = {a["area_id"] for a in alerts}
    for cw in current_weather:
        if cw["area_id"] in affected_ids or cw["risk_level"] in ("high", "critical"):
            affected.append({
                "area_id": cw["area_id"],
                "area_name": cw["area_name"],
                "location": f"{cw['area_name']}, {cw['district']}, {cw['state']}",
                "risk_level": cw["risk_level"],
                "risk_index": cw["risk_index"],
                "population_exposure": _get_population(cw["area_id"]),
                "impact_radius_km": 15 if cw["risk_level"] == "critical" else 10 if cw["risk_level"] == "high" else 5,
                "primary_threat": _primary_threat(cw),
            })
    affected.sort(key=lambda x: {"critical": 0, "high": 1, "moderate": 2, "low": 3}.get(x["risk_level"], 9))

    summary = {
        "generated_at": current_weather[0]["timestamp"] if current_weather else "",
        "hours": hours,
        "seed": seed,
        "current_weather": current_weather,
        "disaster_risk": current_weather,
        "active_alerts": alerts,
        "affected_areas": affected,
        "recent_incidents": incidents,
        "alert_count": len(alerts),
        "affected_count": len(affected),
    }

    (out_dir / "monitor.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "forecast.json").write_text(json.dumps(forecast, indent=2), encoding="utf-8")
    (out_dir / "scored.json").write_text(json.dumps(scored, indent=2), encoding="utf-8")
    (out_dir / "alerts.json").write_text(json.dumps({"alerts": alerts}, indent=2), encoding="utf-8")

    return summary


def _get_population(aid: str) -> int:
    import json as _json
    from .config import DATA_DIR
    areas = _json.loads((DATA_DIR / "areas.json").read_text())
    for a in areas:
        if a["id"] == aid:
            return a["population"]
    return 0


def _primary_threat(cw: dict[str, Any]) -> str:
    t = cw.get("triggers") or []
    if "heavy_rainfall" in t:
        return "Flooding"
    if "high_wind" in t:
        return "High Winds"
    if cw.get("terrain") == "desert":
        return "Heat/Dust Storm"
    if "pressure_drop" in t:
        return "Cyclonic Conditions"
    return "Adverse Weather"

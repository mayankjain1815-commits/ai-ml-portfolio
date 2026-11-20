"""India-wide monitoring orchestrator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .alert_engine import AlertEngine
from .config import DEFAULT_RUNS
from .forecast_gen_india import generate_india_forecast
from .incident_log import IncidentLog
from .risk_model import score_forecast


def run_monitoring_india(hours: int = 120, seed: int = 2026, out_dir: Path | None = None) -> dict[str, Any]:
    out_dir = out_dir or DEFAULT_RUNS
    out_dir.mkdir(parents=True, exist_ok=True)

    forecast = generate_india_forecast(seed=seed, hours=hours)
    scored = score_forecast(forecast)
    alerts = AlertEngine().issue_alerts(scored)
    incidents = IncidentLog().build_incidents(alerts, scored)

    by_area: dict[str, dict[str, Any]] = {}
    for row in scored:
        key = row.get("district_id") or row.get("area_id")
        if key not in by_area or row["timestamp"] > by_area[key]["timestamp"]:
            by_area[key] = row
    current_weather = list(by_area.values())

    affected = []
    affected_ids = {a["area_id"] for a in alerts}
    for cw in current_weather:
        aid = cw.get("district_id") or cw.get("area_id")
        if aid in affected_ids or cw["risk_level"] in ("high", "critical"):
            affected.append({
                "area_id": aid,
                "area_name": cw.get("district_name") or cw.get("area_name"),
                "state": cw.get("state"),
                "location": f"{cw.get('district_name') or cw.get('area_name')}, {cw.get('state')}",
                "risk_level": cw["risk_level"],
                "risk_index": cw["risk_index"],
                "population_exposure": _get_population(),
                "impact_radius_km": 20 if cw["risk_level"] == "critical" else 12 if cw["risk_level"] == "high" else 6,
                "primary_threat": _primary_threat(cw),
                "lat": cw.get("lat"),
                "lon": cw.get("lon"),
            })
    affected.sort(key=lambda x: {"critical": 0, "high": 1, "moderate": 2, "low": 3}.get(x["risk_level"], 9))

    summary = {
        "generated_at": current_weather[0]["timestamp"] if current_weather else "",
        "hours": hours,
        "seed": seed,
        "scope": "india",
        "current_weather": current_weather,
        "disaster_risk": current_weather,
        "active_alerts": alerts,
        "affected_areas": affected,
        "recent_incidents": incidents,
        "alert_count": len(alerts),
        "affected_count": len(affected),
        "areas_monitored": len(current_weather),
    }

    (out_dir / "monitor.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "forecast.json").write_text(json.dumps(forecast, indent=2), encoding="utf-8")
    (out_dir / "scored.json").write_text(json.dumps(scored, indent=2), encoding="utf-8")
    (out_dir / "alerts.json").write_text(json.dumps({"alerts": alerts}, indent=2), encoding="utf-8")

    return summary


def _get_population() -> int:
    import random
    return random.randint(200000, 5000000)


def _primary_threat(cw: dict[str, Any]) -> str:
    t = cw.get("triggers") or []
    if "heavy_rainfall" in t:
        return "Flooding/Waterlogging"
    if "high_wind" in t:
        return "Cyclonic Winds"
    lt = cw.get("location_type") or ""
    if lt == "arid":
        return "Heatwave/Dust Storm"
    if "pressure_drop" in t:
        return "Depression/Cyclone"
    return "Convective Weather"

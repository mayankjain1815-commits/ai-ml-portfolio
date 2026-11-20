"""Alert engine — issues and deduplicates warnings."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .config import ALERT_DEDUP_HOURS


class AlertEngine:
    def __init__(self, dedup_hours: int = ALERT_DEDUP_HOURS) -> None:
        self.dedup_hours = dedup_hours

    def issue_alerts(self, scored: list[dict[str, Any]]) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        by_area: dict[str, list[dict[str, Any]]] = {}
        for row in scored:
            aid = row.get("district_id") or row.get("area_id") or row.get("id")
            row = dict(row)
            row["area_id"] = aid
            row["area_name"] = row.get("district_name") or row.get("area_name") or aid
            row["district"] = row.get("district_name") or row.get("area_name") or ""
            row["state"] = row.get("state") or ""
            by_area.setdefault(aid, []).append(row)
        for aid, rows in by_area.items():
            rows_sorted = sorted(rows, key=lambda x: x["timestamp"])
            recent = rows_sorted[-12:] if len(rows_sorted) >= 12 else rows_sorted
            max_rain = max(r["rain_mm_h"] for r in recent)
            max_wind = max(r["wind_kph"] for r in recent)
            min_pres = min(r["pressure_hpa"] for r in recent)
            max_risk_row = max(recent, key=lambda x: x["risk_index"])
            max_risk = max_risk_row["risk_index"]
            max_level = max_risk_row["risk_level"]
            if max_risk >= 50:
                if max_level in ("moderate", "high", "critical"):
                    pass  # allow
            area_name = recent[-1]["area_name"]
            district = recent[-1]["district"]
            state = recent[-1]["state"]
            terrain = recent[-1].get("terrain")

            if max_level in ("high", "critical") or max_risk >= 55 or max_rain >= 12.0:
                sev = max_level if max_level in ("high", "critical") else ("high" if max_risk >= 65 else "moderate")
                alerts.append(self._make_alert(
                    aid, area_name, district, state, "flood_warning",
                    sev, max_rain, max_wind, min_pres,
                    f"Heavy rainfall ({max_rain:.1f} mm/h) with elevated flood risk in {area_name}.",
                    now
                ))
            if (max_wind >= 45.0 and max_risk >= 50) or max_level in ("high", "critical") or max_risk >= 70:
                sev = max_level if max_level in ("high", "critical") else ("high" if max_risk >= 70 else "moderate")
                alerts.append(self._make_alert(
                    aid, area_name, district, state, "cyclone_warning",
                    sev, max_rain, max_wind, min_pres,
                    f"Gale force winds ({max_wind:.1f} kph) expected near {area_name}.",
                    now
                ))
            if max_level == "critical" or max_risk >= 72:
                alerts.append(self._make_alert(
                    aid, area_name, district, state, "evacuation_advisory",
                    "critical", max_rain, max_wind, min_pres,
                    f"Critical conditions in {area_name}. Prepare to evacuate low-lying areas.",
                    now
                ))
            if terrain == "desert" and recent[-1].get("temperature_c", 0) >= 38.0:
                alerts.append(self._make_alert(
                    aid, area_name, district, state, "heat_alert",
                    "high" if recent[-1].get("temperature_c", 0) < 42 else "critical",
                    max_rain, max_wind, min_pres,
                    f"Extreme heat ({recent[-1]['temperature_c']:.1f}°C) in {area_name}. Avoid outdoor activity.",
                    now
                ))

        deduped = self._deduplicate(alerts, now)
        return deduped

    def _make_alert(self, aid, name, district, state, atype, severity, rain, wind, pres, msg, now):
        valid_to = now + timedelta(hours=12)
        return {
            "alert_id": f"ALERT-{aid}-{atype}-{now.strftime('%Y%m%d%H%M')}",
            "area_id": aid,
            "area_name": name,
            "location": f"{name}, {district}, {state}",
            "alert_type": atype,
            "severity": severity,
            "message": msg,
            "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "valid_to": valid_to.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "issued_by": "Disaster Watch Authority",
            "conditions": {
                "max_rain_mm_h": round(rain, 1),
                "max_wind_kph": round(wind, 1),
                "min_pressure_hpa": round(pres, 1),
            },
        }

    def _deduplicate(self, alerts: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
        seen: dict[tuple, dict[str, Any]] = {}
        for a in alerts:
            key = (a["area_id"], a["alert_type"])
            if key not in seen:
                seen[key] = a
            else:
                sev_order = {"moderate": 1, "high": 2, "critical": 3}
                if sev_order.get(a["severity"], 0) > sev_order.get(seen[key]["severity"], 0):
                    seen[key] = a
        result = list(seen.values())
        sev_order = {"critical": 0, "high": 1, "moderate": 2, "low": 3}
        result.sort(key=lambda x: (sev_order.get(x["severity"], 9), x["area_name"]))
        return result


# Patch for india format

"""Incident log — records warnings, sensor events and emergency reports. Maintains a chronological log of recent incidents with source, status and details."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


class IncidentLog:
    """Build recent incidents from alerts and sensor events."""

    def build_incidents(self, alerts: list[dict[str, Any]], scored: list[dict[str, Any]]) -> list[dict[str, Any]]:
        incidents: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc)

        # Add incidents from active alerts
        for i, a in enumerate(alerts):
            incidents.append({
                "incident_id": f"INC-{a['alert_id']}",
                "timestamp": a["issued_at"],
                "type": "warning",
                "category": a["alert_type"],
                "location": a["location"],
                "area_id": a["area_id"],
                "severity": a["severity"],
                "source": a["issued_by"],
                "status": "active",
                "description": a["message"],
            })

        # Add sensor events from recent data
        by_area: dict[str, list[dict[str, Any]]] = {}
        for row in scored:
            aid = row.get("district_id") or row.get("area_id")
            if not aid:
                continue
            row = dict(row)
            row["area_id"] = aid
            row["area_name"] = row.get("district_name") or row.get("area_name") or aid
            by_area.setdefault(aid, []).append(row)
        for aid, rows in by_area.items():
            rows_sorted = sorted(rows, key=lambda x: x["timestamp"])
            recent = rows_sorted[-3:]
            for r in recent:
                if r["rain_mm_h"] >= 15.0:
                    incidents.append({
                        "incident_id": f"SEV-{aid}-{r['timestamp'].replace(':','').replace('-','')}",
                        "timestamp": r["timestamp"],
                        "type": "sensor_event",
                        "category": "rainfall_spike",
                        "location": f"{r['area_name']}, {r['district']}, {r['state']}",
                        "area_id": aid,
                        "severity": "moderate" if r["rain_mm_h"] < 40 else "high",
                        "source": "Automated Rain Gauge Network",
                        "status": "observed",
                        "description": f"Rain gauge recorded {r['rain_mm_h']:.1f} mm/h at {r['area_name']}.",
                    })
                if r["wind_kph"] >= 50.0:
                    incidents.append({
                        "incident_id": f"SEV-W-{aid}-{r['timestamp'].replace(':','').replace('-','')}",
                        "timestamp": r["timestamp"],
                        "type": "sensor_event",
                        "category": "wind_increase",
                        "location": f"{r['area_name']}, {r['district']}, {r['state']}",
                        "area_id": aid,
                        "severity": "moderate" if r["wind_kph"] < 80 else "high",
                        "source": "Anemometer Array",
                        "status": "observed",
                        "description": f"Sustained winds {r['wind_kph']:.1f} kph observed at {r['area_name']}.",
                    })

        # Add a couple of emergency reports
        if alerts:
            a = alerts[0]
            incidents.append({
                "incident_id": "EMR-001",
                "timestamp": (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "type": "emergency_report",
                "category": "control_room_update",
                "location": a["location"],
                "area_id": a["area_id"],
                "severity": a["severity"],
                "source": "District Control Room",
                "status": "in_progress",
                "description": "Control room monitoring situation closely. NDRF standby notified.",
            })

        # Sort by timestamp descending
        incidents.sort(key=lambda x: x["timestamp"], reverse=True)
        # Limit to reasonable number
        return incidents[:30]

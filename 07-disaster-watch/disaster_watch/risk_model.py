"""Risk model — computes disaster risk level per area from weather signals.

Uses weighted rules (rainfall, wind, pressure drop, humidity) to produce a
numeric risk index 0-100 and a categorical level.
"""

from __future__ import annotations

from typing import Any

from .config import (
    HUMIDITY_HIGH_PCT,
    PRESSURE_DROP_HPA,
    RAIN_ALERT_MM_H,
    RISK_HIGH_MAX,
    RISK_LOW_MAX,
    RISK_MOD_MAX,
    WIND_ALERT_KPH,
)


class RiskModel:
    W_RAIN = 0.35
    W_WIND = 0.25
    W_PRESSURE = 0.20
    W_HUMIDITY = 0.10
    W_VISIBILITY = 0.10

    def score_row(self, row: dict[str, Any], area_meta: dict[str, Any] | None = None) -> dict[str, Any]:
        rain = float(row.get("rain_mm_h", 0.0))
        wind = float(row.get("wind_kph", 0.0))
        pres = float(row.get("pressure_hpa", 1010.0))
        hum = float(row.get("humidity_pct", 50.0))
        vis = float(row.get("visibility_km", 10.0))
        terrain = row.get("terrain", "inland_plain")

        rain_n = min(1.0, rain / 60.0)
        wind_n = min(1.0, wind / 120.0)
        pres_n = min(1.0, max(0.0, (1010.0 - pres) / 15.0))
        hum_n = min(1.0, max(0.0, (hum - 60.0) / 40.0))
        vis_n = min(1.0, max(0.0, (10.0 - vis) / 9.5))

        index = (
            self.W_RAIN * rain_n
            + self.W_WIND * wind_n
            + self.W_PRESSURE * pres_n
            + self.W_HUMIDITY * hum_n
            + self.W_VISIBILITY * vis_n
        ) * 100.0

        if terrain in ("coastal_lowland", "coastal_harbor", "urban_coastal"):
            index *= 1.08
        elif terrain == "river_valley":
            index *= 1.06
        elif terrain == "desert":
            index = index * 0.7 + self.W_WIND * wind_n * 100.0 * 0.6
        index = max(0.0, min(100.0, index))

        level = self._level(index)
        triggers = self._triggers(rain, wind, pres, hum)
        return {
            "risk_index": round(index, 1),
            "risk_level": level,
            "components": {
                "rain_norm": round(rain_n, 3),
                "wind_norm": round(wind_n, 3),
                "pressure_norm": round(pres_n, 3),
                "humidity_norm": round(hum_n, 3),
                "visibility_norm": round(vis_n, 3),
            },
            "triggers": triggers,
        }

    def _level(self, index: float) -> str:
        if index < RISK_LOW_MAX:
            return "low"
        if index < RISK_MOD_MAX:
            return "moderate"
        if index < RISK_HIGH_MAX:
            return "high"
        return "critical"

    def _triggers(self, rain: float, wind: float, pres: float, hum: float) -> list[str]:
        t: list[str] = []
        if rain >= RAIN_ALERT_MM_H:
            t.append("heavy_rainfall")
        if wind >= WIND_ALERT_KPH:
            t.append("high_wind")
        if (1010.0 - pres) >= PRESSURE_DROP_HPA:
            t.append("pressure_drop")
        if hum >= HUMIDITY_HIGH_PCT:
            t.append("high_humidity")
        return t


def score_forecast(forecast: list[dict[str, Any]]) -> list[dict[str, Any]]:
    model = RiskModel()
    out: list[dict[str, Any]] = []
    for row in forecast:
        scored = dict(row)
        scored.update(model.score_row(row))
        out.append(scored)
    return out

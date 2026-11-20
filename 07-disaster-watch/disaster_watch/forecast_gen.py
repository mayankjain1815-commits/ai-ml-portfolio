"""Forecast generator — builds deterministic weather forecasts per area.

Demo mode uses a seeded random generator with a controlled storm ramp so the
risk model and alerts behave predictably. Real feeds can replace this module
without changing the rest of the pipeline.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import DATA_DIR, DEFAULT_HOURS, DEFAULT_SEED


class ForecastGenerator:
    """Generate hourly forecasts for monitored areas."""

    def __init__(self, seed: int = DEFAULT_SEED, hours: int = DEFAULT_HOURS) -> None:
        self.seed = seed
        self.hours = hours
        self.rng = random.Random(seed)
        self.areas = self._load_areas()

    def _load_areas(self) -> list[dict[str, Any]]:
        path = DATA_DIR / "areas.json"
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def generate(self) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        rows: list[dict[str, Any]] = []
        for h in range(self.hours):
            ts = now + timedelta(hours=h)
            ramp = 0.0
            if 40 <= h <= 60:
                ramp = (h - 40) / 20.0
            for area in self.areas:
                row = self._row_for_area(area, ts, h, ramp)
                rows.append(row)
        return rows

    def _row_for_area(self, area: dict[str, Any], ts: datetime, h: int, ramp: float) -> dict[str, Any]:
        aid = area["id"]
        terrain = area["terrain"]
        base_rain = 2.0 if terrain == "coastal_lowland" else 1.0
        base_temp = 28.0
        base_hum = 70.0
        base_wind = 15.0
        base_pres = 1008.0
        base_vis = 8.0

        if terrain in ("coastal_lowland", "coastal_harbor", "urban_coastal"):
            rain = base_rain + ramp * (35.0 + self.rng.uniform(-5, 10))
            wind = base_wind + ramp * (55.0 + self.rng.uniform(-10, 15))
            pres = base_pres - ramp * (8.0 + self.rng.uniform(0, 2))
            hum = min(98.0, base_hum + ramp * (20.0 + self.rng.uniform(-5, 5)))
        elif terrain == "river_valley":
            rain = base_rain + ramp * 25.0 + self.rng.uniform(-3, 8)
            wind = base_wind + self.rng.uniform(5, 12)
            pres = base_pres - ramp * 3.0
            hum = min(96.0, base_hum + 10.0)
        elif terrain == "desert":
            rain = max(0.0, self.rng.uniform(0, 2))
            wind = base_wind + ramp * 20.0 + self.rng.uniform(0, 15)
            pres = base_pres + self.rng.uniform(-2, 2)
            hum = max(15.0, 25.0 - ramp * 10.0)
            base_temp = 38.0
        else:
            rain = base_rain + ramp * 12.0 + self.rng.uniform(-2, 6)
            wind = base_wind + ramp * 15.0
            pres = base_pres - ramp * 2.0
            hum = base_hum + 5.0

        rain = max(0.0, rain + self.rng.uniform(-2, 2))
        temp = base_temp + self.rng.uniform(-2, 3)
        hum = max(10.0, min(99.0, hum + self.rng.uniform(-3, 3)))
        wind = max(0.0, wind + self.rng.uniform(-3, 5))
        pres = pres + self.rng.uniform(-1, 1)
        vis = max(0.5, base_vis - ramp * 4.0 + self.rng.uniform(-1, 1))
        if terrain == "desert" and ramp > 0.3:
            vis = max(0.2, vis - ramp * 3.0)

        return {
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "area_id": aid,
            "area_name": area["name"],
            "district": area["district"],
            "state": area["state"],
            "rain_mm_h": round(rain, 2),
            "temperature_c": round(temp, 1),
            "humidity_pct": round(hum, 1),
            "wind_kph": round(wind, 1),
            "pressure_hpa": round(pres, 1),
            "visibility_km": round(vis, 2),
            "terrain": terrain,
            "ramp_phase": round(ramp, 3),
        }


def generate_forecast(seed: int = DEFAULT_SEED, hours: int = DEFAULT_HOURS) -> list[dict[str, Any]]:
    gen = ForecastGenerator(seed=seed, hours=hours)
    return gen.generate()

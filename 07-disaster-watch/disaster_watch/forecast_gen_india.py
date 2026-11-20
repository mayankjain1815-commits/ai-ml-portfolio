"""India-wide forecast generator with hierarchical granularity."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import DATA_DIR, DEFAULT_HOURS


class IndiaForecastGenerator:
    def __init__(self, seed: int = 2026, hours: int = 120) -> None:
        self.seed = seed
        self.hours = hours
        self.rng = random.Random(seed)
        self.regions = self._load_regions()

    def _load_regions(self) -> dict[str, Any]:
        path = DATA_DIR / "india_regions.json"
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def generate(self) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        rows: list[dict[str, Any]] = []
        for h in range(self.hours):
            ts = now + timedelta(hours=h)
            ramp = 0.0
            if 60 <= h <= 96:
                ramp = (h - 60) / 36.0
            for d in self.regions["districts"]:
                row = self._row_for_district(d, ts, h, ramp)
                rows.append(row)
        return rows

    def _row_for_district(self, d: dict[str, Any], ts: datetime, h: int, ramp: float) -> dict[str, Any]:
        dtype = d["type"]
        base_rain = 2.0
        base_temp = 28.0
        base_hum = 70.0
        base_wind = 12.0
        base_pres = 1008.0
        base_vis = 8.0

        if dtype == "coastal":
            rain = base_rain + ramp * (38.0 + self.rng.uniform(-6, 12))
            wind = base_wind + ramp * (58.0 + self.rng.uniform(-12, 18))
            pres = base_pres - ramp * (9.0 + self.rng.uniform(0, 3))
            hum = min(98.0, base_hum + ramp * (22.0 + self.rng.uniform(-6, 6)))
        elif dtype == "riverine":
            rain = base_rain + ramp * 28.0 + self.rng.uniform(-4, 10)
            wind = base_wind + self.rng.uniform(6, 14)
            pres = base_pres - ramp * 4.0
            hum = min(96.0, base_hum + 12.0)
        elif dtype == "valley" or dtype == "flood-prone":
            rain = base_rain + ramp * 32.0 + self.rng.uniform(-5, 12)
            wind = base_wind + self.rng.uniform(4, 10)
            pres = base_pres - ramp * 5.0
            hum = min(97.0, base_hum + 15.0)
        elif dtype == "arid":
            rain = max(0.0, self.rng.uniform(0, 3))
            wind = base_wind + ramp * 22.0 + self.rng.uniform(2, 18)
            pres = base_pres + self.rng.uniform(-2, 3)
            hum = max(12.0, 22.0 - ramp * 12.0)
            base_temp = 40.0
        elif dtype == "metro" or dtype == "urban":
            rain = base_rain + ramp * 16.0 + self.rng.uniform(-3, 8)
            wind = base_wind + ramp * 18.0 + self.rng.uniform(-2, 8)
            pres = base_pres - ramp * 3.0
            hum = base_hum + 8.0
        else:
            rain = base_rain + ramp * 14.0 + self.rng.uniform(-3, 7)
            wind = base_wind + ramp * 16.0
            pres = base_pres - ramp * 2.5
            hum = base_hum + 6.0

        rain = max(0.0, rain + self.rng.uniform(-3, 3))
        temp = base_temp + self.rng.uniform(-3, 4)
        hum = max(8.0, min(99.0, hum + self.rng.uniform(-4, 4)))
        wind = max(0.0, wind + self.rng.uniform(-4, 6))
        pres = pres + self.rng.uniform(-1.5, 1.5)
        vis = max(0.3, base_vis - ramp * 5.0 + self.rng.uniform(-1.5, 1.5))
        if dtype == "arid" and ramp > 0.25:
            vis = max(0.15, vis - ramp * 4.0)

        return {
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "region_type": "district",
            "district_id": d["id"],
            "district_name": d["name"],
            "state": d["state"],
            "lat": d["lat"],
            "lon": d["lon"],
            "location_type": dtype,
            "rain_mm_h": round(rain, 2),
            "temperature_c": round(temp, 1),
            "humidity_pct": round(hum, 1),
            "wind_kph": round(wind, 1),
            "pressure_hpa": round(pres, 1),
            "visibility_km": round(vis, 2),
            "ramp_phase": round(ramp, 3),
        }


def generate_india_forecast(seed: int = 2026, hours: int = 120) -> list[dict[str, Any]]:
    gen = IndiaForecastGenerator(seed=seed, hours=hours)
    return gen.generate()

# 07. Disaster Watch

> Forecast-driven disaster monitoring: collect weather forecasts and environmental signals, estimate area-level risk, issue warnings, and give authorities a single dashboard to act on.

**Inspired by:** National weather alerting systems (IMD-style bulletins, NWS CAP concepts) and operational control rooms — rebuilt from first principles so every calculation (risk scoring, alerting, deduplication) stays visible.

## What it does

- **Current weather** — Displays rainfall, temperature, humidity, wind, pressure and visibility for every monitored area, pulled from a deterministic forecast stream in demo mode.
- **Disaster risk level** — Scores each area against flood/cyclone/heat/storm rules using weighted environmental thresholds, producing `low / moderate / high / critical` with a numeric risk index (0-100).
- **Active alerts** — Shows warnings currently issued for specific locations, with severity, reason, validity window and issuing authority channel.
- **Affected areas** — Lists locations potentially affected by an active disaster, with population exposure and projected impact radius.
- **Recent incidents** — Records warnings, sensor events and emergency reports in chronological order with source, status and timestamps.

## Color scheme

- **Ice Silver** — backgrounds, cards, dividers (`#f7f9fb`, `#eef2f6`, `#c9d2dc`)
- **Deep Aubergine** — headers, panels, text emphasis (`#2a1028`, `#3b1d36`, `#4f2a45`)
- **Marigold** — alerts, calls to action, highlights (`#f5b700`, `#ffcc33`, `#d99a00`)

## Quick start

```bash
cd 07-disaster-watch

# Full pipeline: generate forecast data → run risk model → produce alerts
../.venv/bin/python -m disaster_watch demo

# Start the authority dashboard (http://127.0.0.1:5107)
../.venv/bin/python -m disaster_watch dashboard

# Other commands
../.venv/bin/python -m disaster_watch simulate --hours 72
../.venv/bin/python -m disaster_watch report
../.venv/bin/python -m disaster_watch forecast
```

## How it works

```
forecast_gen.py  -> builds deterministic hourly forecasts per monitored area
risk_model.py     -> applies rule weights (rain, wind, humidity, pressure) -> risk index + level
alert_engine.py   -> issues alerts when thresholds crossed, deduplicates by (area, type)
incident_log.py   -> appends warnings/sensor/emergency events with timestamps
dashboard.py      -> serves the authority view with live panels + JSON APIs
```

Walkthrough (demo run):
1. `forecast_gen` creates 72 hours of forecast data for 6 monitored areas with a seeded storm ramp.
2. `risk_model` evaluates each hour/area, computes weighted contributions and produces risk levels.
3. `alert_engine` creates active alerts for high/critical areas, deduplicating repeats within a window.
4. `incident_log` records recent incidents from alerts and simulated sensor events.
5. Dashboard reads `runs/latest/` and renders all five required sections with the ice silver/aubergine/marigold palette.

## Demo mode vs real mode

| Aspect | Demo (no key) | Real mode (with keys/env) |
| --- | --- | --- |
| Forecasts | Deterministic seeded generator | Ingest from IMD/NWS/API feeds |
| Risk model | Hand-crafted weighted rules (same formula) | Same formula, tuned weights from history |
| Alerts | Local alert engine with dedup | Push to SMS/email/cap feeds via connectors |
| Incidents | Synthetic but realistic events | Ingest from sensors/authorities/CAP |
| Dashboard | Fully functional offline | Same UI, live data sources |

## Project structure

```text
07-disaster-watch/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── disaster_watch/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── config.py
│   ├── forecast_gen.py
│   ├── risk_model.py
│   ├── alert_engine.py
│   ├── incident_log.py
│   ├── monitor.py
│   ├── dashboard.py
│   ├── data/
│   │   └── areas.json
│   ├── templates/
│   │   └── index.html
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       └── dashboard.js
│   └── utils/
│       ├── __init__.py
│       └── timeutil.py
├── runs/
└── tests/
    ├── test_forecast.py
    ├── test_risk.py
    └── test_alerts.py
```

## Explain it like I'm 19

Imagine a control room during monsoon. Sensors and weather forecasts feed in; a simple set of rules says "if heavy rain + rising wind for hours, flood risk goes up". When it crosses a line, the room issues warnings to towns in the path and logs everything. This dashboard shows exactly that - current weather, who is at risk, what warnings are active, which areas are affected, and what happened recently - without needing internet data.

## Tests

```bash
cd 07-disaster-watch
../../.venv/bin/python -m pytest -q
```

All tests run offline with no API keys.

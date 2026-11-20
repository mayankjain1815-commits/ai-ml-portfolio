# 08. SENTINEL · IoT Disaster Command

> An end-to-end early-warning platform for a three-node ESP32/LoRa sensor network: live telemetry, a transparent risk engine, authority-grade alerting, a geographic common operating picture, an immutable incident log, and a command console that can override, acknowledge, evacuate and test emergency channels.

**Sector:** `SECTOR-04 · Nashik Basin, Maharashtra`  
**Stack:** Node.js 22+ · Express 5 · native `node:sqlite` · `ws` · React 19 · Vite 7 · Leaflet  
**Ports:** app `5108` · Vite dev server `5109`  
**Demo mode:** fully offline, deterministic, and seeded with a live three-node emergency.

---

## Why this project exists

Most IoT dashboards stop at “here is a chart”. SENTINEL closes the operational loop:

```
ESP32 sensors → LoRa gateway → HTTP POST / WebSocket → validation → SQLite
                                                              ↓
                       ┌──────────────────────────────────────┴───────────────────────┐
                       ↓                                                              ↓
              deterministic risk engine                                    browser WebSocket
       flood · landslide · air quality · heat                            (live snapshot push)
                       ↓                                                              ↓
          alert dedup / escalation / auto-resolution            SENTINEL command interface
                       ↓                                                              ↓
                incident audit trail  ←──────────── authority acknowledgments ───────┘
```

Every layer is executable. There are no mock UI states, hard-coded dashboard cards, or “coming soon” panels.

---

## Feature tour

| Area | What ships |
| --- | --- |
| **Overview** | Sector risk band, population exposure, live weather aggregate, node cards with sparklines, risk gauge, latest alerts, recent incidents. |
| **Sensor telemetry** | Exact per-node temperature, humidity, rainfall, water level, vibration, AQI, SOS, battery, RSSI/SNR, GPS and packet age. |
| **Risk engine** | Continuous 0–100 scoring for flood, landslide, air quality and heat; terrain/slope weighting; compound-hazard bonus; SOS override; per-factor explainability. |
| **Alerts** | Automated and manual warnings, severity filter, acknowledgment, dedup by `(node, hazard)`, escalation, hysteresis-based auto-resolution and an SOS channel. |
| **Map** | Leaflet map with a fully offline custom vector basemap, strict palette, sector bounds, GPS-accurate node markers, risk halos, affected-area rings, popups and node inspection. |
| **Incident log** | Server-side search, severity/event/status/source filters, pagination, detail modal, machine metadata and CSV export. |
| **Authority console** | Acknowledge one/all, risk override with expiry, clear override, evacuation order, all-clear, siren toggle, SOS test, audit history. |
| **Node health** | Online/offline classification, battery percentage, RSSI link quality, packet counts, last-seen age, per-node 6-hour history. |
| **Realtime** | WebSocket snapshot push with reconnect/backoff, REST fallback polling, toast alerts for newly arrived warnings. |
| **Simulator** | Correlated 4-second telemetry—not random noise—that grows a flood, pulses slope vibration and keeps AQI elevated. |

The UI uses only **Ice Silver `#DDD3E8`**, **Deep Aubergine `#3A0F34`**, and **Marigold `#EAAA00`** (plus tints/tones of those three) across the entire product.

---

## Quick start

```bash
cd 08-sentinel-iot
npm install

# Development: API on :5108, Vite HMR UI on :5109
npm run dev
# open http://localhost:5109

# Production-style: build once, serve UI + API + WebSocket from :5108
npm run build
npm start
# open http://localhost:5108
```

On first boot the database is created and seeded with three nodes, ~37 history points per node, three alerts and a populated incident log. The simulator is **on by default** and emits a new reading for all three nodes every 4 seconds.

### Useful commands

```bash
npm test                  # 38 node:test cases (risk, validation, telemetry, API, WebSocket)
npm run build             # Vite production bundle
npm start                 # production server on :5108
npm run dev               # API + Vite concurrently
```

### Reset the demo

Stop the server, delete the database files, then start again:

```bash
rm -f data/sentinel.db data/sentinel.db-shm data/sentinel.db-wal
npm start
```

---

## Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `5108` | HTTP/WebSocket port |
| `NODE_ENV` | `development` | `production` serves `dist/` and enables caching |
| `DATABASE_PATH` | `./data/sentinel.db` | SQLite file; use `:memory:` only in tests |
| `GATEWAY_KEY` | `gw-sentinel-demo-key` | Shared gateway secret for HTTP and gateway WebSocket |
| `SIMULATION` | `true` | Background demo traffic |
| `SIMULATION_INTERVAL_MS` | `4000` | Simulator tick (minimum 2 s) |
| `OPERATOR_NAME` | `Duty Officer M. Rao` | Audit identity shown in the console |
| `REGION_NAME` | `Nashik Basin` | Display region |
| `EMERGENCY_NUMBER` | `112` | Shown in command/emergency messaging |
| `RETENTION_DAYS` | `30` | Telemetry/incident retention window |

> Command endpoints are intentionally open in this demo so the UI works without accounts. For a real deployment put SENTINEL behind authenticated reverse-proxy/SSO and set a strong `GATEWAY_KEY`. See [Security notes](#security-notes).

---

## Network and node profile

| Node | Location | Terrain | Population | Demo behaviour |
| --- | --- | --- | --- | --- |
| `SN-NASH-01` | Godavari Ghat | riverine | 18,400 | Rising water → **Severe** flood |
| `SN-NASH-02` | Panchavati Ridge | slope (96/100) | 9,200 | Saturated slope + vibration → **High/Severe** landslide |
| `SN-NASH-03` | Darna Spillway | reservoir | 5,600 | Elevated AQI → **Moderate** air quality |

Exact coordinates live in `server/site.js` and are rendered unchanged on the map (`19.9975, 73.7898`, `20.0234, 73.8120`, `20.0488, 73.8425`).

---

## Risk engine

`server/risk-engine.js` is pure and deterministic—the same function is used by live telemetry, the simulator, REST ingestion and tests.

| Score | Level | Operational meaning |
| --- | --- | --- |
| `< 25` | **Low** | Normal monitoring |
| `25 – 49.9` | **Moderate** | Advisory / sensitive groups |
| `50 – 74.9` | **High** | Prepare / pre-position resources |
| `≥ 75` | **Severe** | Immediate action / evacuation |

Hazard scoring (each contribution is a ramp from onset to saturation):

- **Flood** — water depth 55%, rain intensity 30%, humidity 8%, rising-water trend 7%; riverine multiplier `1.12`.
- **Landslide** — rain 50%, ground vibration 20%, humidity 10%, static slope exposure 20%; slope multiplier `1.12`.
- **Air quality** — AQI 85%, humidity 5%, heat 10%.
- **Heat** — temperature 80%, humidity 20%.
- **Compound** — if flood ≥ 50 *and* landslide ≥ 50, add **+6** to the primary score.
- **SOS** — a manual SOS forces a `severe` / 100 primary hazard.

Every snapshot includes the top contributing factors, all hazard sub-scores, the primary hazard and a human-readable advisory. An operator override changes the *effective* risk but preserves `sensorRisk`, so the audit record always distinguishes human judgment from sensor measurement.

---

## Simulation

`server/simulator.js` builds correlated readings from each node's previous state:

- Godavari water level tracks rainfall (`rain - 17`) with bounded drift and jitter, holding severe flood conditions.
- Panchavati vibration pulses periodically instead of firing randomly, so the UI demonstrates intermittent slope movement.
- Darna AQI oscillates around a moderate public-health advisory.
- Battery drains slowly and occasionally recovers, with GPS jitter of ~2.5 m.
- Packets carry `SIM-*` IDs and are ingested through the same `TelemetryService` as real hardware.

Disable with `SIMULATION=false` when connecting physical nodes.

---

## API

All responses are JSON with `ok: true|false`. Errors include `{ ok: false, error, issues? }`.

| Method | Route | Notes |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness, version, node counts, simulation status |
| `GET` | `/api/meta` | Sector metadata, operator, simulation status |
| `GET` | `/api/dashboard` | Complete UI snapshot (nodes, alerts, incidents, gateway, summary, weather, evacuation, siren) |
| `GET` | `/api/nodes` | Node list with latest reading, risk, health |
| `GET` | `/api/nodes/:id` | Node + 6-hour history |
| `GET` | `/api/nodes/:id/history?hours=6` | History, 1–168 hours |
| `GET` | `/api/alerts?status=active\|acknowledged\|resolved\|all&limit=60` | Alert queue |
| `GET` | `/api/incidents` | Search/filter/paginate: `search,severity,type,status,source,from,to,limit,offset` |
| `GET` | `/api/incidents/stats` | 24-hour counts by severity |
| `GET` | `/api/incidents/export.csv` | CSV export (same filters, max 5,000 rows) |
| `POST` | `/api/v1/telemetry` | Single or batched telemetry; requires `X-Gateway-Key` |
| `POST` | `/api/alerts/:id/acknowledge` | Optional `{ operator }` or `X-Operator-Name` |
| `POST` | `/api/alerts/acknowledge-all` | Acknowledge every active alert |
| `POST` | `/api/commands/override` | `{ nodeId, level, note, durationMinutes }` |
| `DELETE` | `/api/nodes/:id/override` | Restore automatic risk |
| `POST` | `/api/commands/evacuation` | `{ nodeId?, reason }` |
| `POST` | `/api/commands/all-clear` | Clear active evacuation |
| `POST` | `/api/commands/siren` | `{ enabled: boolean }` |
| `POST` | `/api/commands/test-sos` | `{ nodeId }`; writes a severe SOS alert |

### Telemetry payload

```json
{
  "nodeId": "SN-NASH-01",
  "lat": 19.9975,
  "lon": 73.7898,
  "temp": 28.4,
  "humidity": 92,
  "rain": 24.6,
  "waterLevel": 118.2,
  "vibration": 8,
  "aqi": 84,
  "sos": false,
  "battery": 3.82,
  "rssi": -67,
  "snr": 7.6,
  "timestamp": "2026-10-26T14:32:00.000Z",
  "packetId": "SN-12842"
}
```

`vibration` accepts `true/false` or `0–100`. `lat`/`lon`, `rssi`, `snr`, `timestamp` and `packetId` are optional; the remaining fields are required. Batches use `{ "gatewayId": "GW-NSK-01", "readings": [ ... ] }` with up to 24 readings. Full schema and examples: [`docs/payload-schema.md`](docs/payload-schema.md).

```bash
curl -X POST http://localhost:5108/api/v1/telemetry \
  -H 'Content-Type: application/json' \
  -H 'X-Gateway-Key: gw-sentinel-demo-key' \
  -d '{"nodeId":"SN-NASH-01","lat":19.9975,"lon":73.7898,"temp":28.4,"humidity":92,"rain":24.6,"waterLevel":118.2,"vibration":8,"aqi":84,"sos":false,"battery":3.82}'
```

### WebSocket

| Endpoint | Authentication | Purpose |
| --- | --- | --- |
| `ws://localhost:5108/ws` | none (read-only) | Browser snapshots |
| `ws://localhost:5108/ws/gateway?key=...` | `?key=`, `X-Gateway-Key` or `Authorization: Bearer` | Gateway telemetry ingestion |

Browser clients receive a `snapshot` frame immediately, then on every ingest/simulator tick. `{ "type": "ping" }` returns `pong`; heartbeats run every 30 s. Gateway messages may be a single reading or a batch and receive `ack` / `error` frames. See [`docs/esp32-integration.md`](docs/esp32-integration.md).

---

## Project structure

```text
08-sentinel-iot/
├── server/
│   ├── index.js                 HTTP + WebSocket bootstrap, simulator, retention
│   ├── app.js                   Express routes, auth, validation, CSV, static UI
│   ├── config.js                .env-backed runtime configuration
│   ├── store.js                 node:sqlite schema and queries
│   ├── site.js                  sector, nodes, gateway, seed profiles
│   ├── seed.js                  deterministic first-boot demo network
│   ├── validation.js            Zod schemas for readings and commands
│   ├── risk-engine.js           pure hazard scoring
│   ├── telemetry-service.js     ingest, dedup, escalation, resolution, SOS
│   ├── dashboard-service.js     snapshot, effective override risk, node health
│   ├── command-service.js       acknowledge/evacuate/override/siren/SOS
│   ├── simulator.js             correlated three-node telemetry
│   └── realtime.js              browser + gateway WebSockets
├── web/src/
│   ├── App.jsx                  hash routing, live snapshot, toasts, modals
│   ├── components/              SensorCard, RiskGauge, AlertBanner, InteractiveMap,
│   │                            IncidentTable, AuthorityConsole, NodeDetail, …
│   ├── views/                   Overview, MapView, AlertsView, IncidentsView, CommandView
│   ├── lib/                     API client, formatting, map geometry, siren, live socket
│   └── styles.css               palette-strict responsive design system
├── tests/                       node:test suites + helpers
├── docs/                        payload schema and ESP32 integration guide
├── firmware/                    ESP32 node + LoRa gateway sketches
├── data/                        SQLite database (gitignored)
└── dist/                        production build (gitignored)
```

---

## ESP32 hardware integration

Complete sketches and wiring notes live in [`firmware/`](firmware/). The reference node uses:

- ESP32 DevKit v1 + SX1276 LoRa (865–867 MHz for India)
- DHT22 temperature/humidity
- Tipping-bucket rain gauge (GPIO interrupt)
- HC-SR04 ultrasonic water-level sensor
- SW-420 vibration switch
- MQ-135 air-quality sensor (warm-up + calibration required)
- Momentary SOS button
- 18650 cell via divider on an ADC pin

The gateway receives LoRa JSON, validates packet integrity, batches up to 24 readings, and posts to `/api/v1/telemetry` with the gateway key. Wiring tables, libraries, calibration steps and a WebSocket alternative are in [`docs/esp32-integration.md`](docs/esp32-integration.md).

---

## Security notes

- Gateway ingestion requires the shared key; telemetry and command routes are rate limited (120 and 60 requests/min per IP in non-test environments).
- Helmet sets a strict CSP; the production build serves only self-hosted assets and data/blob images. Leaflet tiles are **not** loaded from a third party—the basemap is generated locally.
- Zod `.strict()` schemas reject unknown fields and out-of-range sensor values.
- SQL uses parameterized statements throughout; the SQLite file is local-only.
- Incident records are append-only through the service layer; acknowledgments add linked audit events instead of mutating the original warning.
- **Demo limitation:** authority command routes are unauthenticated so reviewers can operate the console. Put them behind authenticated SSO / mTLS / an API gateway before using this with real communities.

---

## Tests

```bash
npm test
```

Coverage includes:

- Risk thresholds, SOS, compound-flood bonus and factor explanations.
- Payload validation, optional fields, malformed coordinates and gateways.
- Single/batch HTTP ingestion, authentication, deduplication, escalation and auto-resolution hysteresis.
- Dashboard snapshot shape, overrides, node health, commands, incidents, search/filter, CSV export.
- Gateway WebSocket auth/ack/error paths and browser snapshot/ping behaviour.
- Persistence via an in-memory SQLite database per test.

No network access, hardware, API keys or external services are required.

---

## Design decisions

- **Native `node:sqlite`** removes a native-compilation dependency while still giving durable WAL-backed storage and real SQL.
- **Deterministic risk engine** means the same score can be explained in an incident review, replayed in a test, and shown in the UI.
- **Offline vector basemap** keeps the strict palette intact, avoids map-tile API keys, and lets the demo run with no internet.
- **Hash routing** works behind any static host and avoids server-side SPA fallback complexity.
- **Simulation is a first-class ingestion path**, not a separate frontend fixture: simulated packets go through validation, persistence, risk evaluation and alerting exactly like hardware.

---

## License

Learning portfolio project. All code, seed data and documentation are original. Map geometry is derived from the sector bounds at runtime, not from a third-party tile service.

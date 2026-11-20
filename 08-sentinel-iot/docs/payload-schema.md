# Telemetry payload schema

SENTINEL accepts telemetry over HTTP (`POST /api/v1/telemetry`) and WebSocket (`/ws/gateway`). Both transports share the same Zod schema in [`server/validation.js`](../server/validation.js), so a packet that is accepted by one is accepted by the other.

- Protocol ID: `sentinel.telemetry.v1`
- Content type: `application/json`
- Maximum HTTP body: `128 kb`
- Maximum WebSocket frame: `64 kb`
- Maximum readings per batch: `24`

---

## 1. Single reading (HTTP)

```http
POST /api/v1/telemetry
Content-Type: application/json
X-Gateway-Key: gw-sentinel-demo-key
```

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

### Field contract

| Field | Type | Required | Range / format | Unit | Notes |
| --- | --- | --- | --- | --- | --- |
| `nodeId` | string | **yes** | 3–64 chars, trimmed | — | Must be a node registered in `server/site.js`. Unknown IDs are rejected at ingestion. |
| `lat` | number \| null | no | −90…90 | degrees | GPS latitude from the node. `null` means no fix. |
| `lon` | number \| null | no | −180…180 | degrees | GPS longitude from the node. |
| `temp` | number | **yes** | −40…85 | °C | Air temperature |
| `humidity` | number | **yes** | 0…100 | %RH | Relative humidity |
| `rain` | number | **yes** | 0…500 | mm/h | Rainfall intensity (not a daily total) |
| `waterLevel` | number | **yes** | 0…1500 | cm | Distance from sensor datum to water surface; mount height must be applied in firmware |
| `vibration` | boolean \| number | **yes** | `true`/`false` or 0…100 | level | Boolean is normalized to `100`/`0`; numeric values represent an impulse-intensity scale |
| `aqi` | number | **yes** | 0…1000 | AQI | Calibrated air-quality index |
| `sos` | boolean | no (default `false`) | — | — | Forces a severe manual-SOS alert and 100 risk score |
| `battery` | number | **yes** | 0…5.5 | V | Cell voltage; UI converts to a percentage using 3.30–4.20 V |
| `rssi` | number | no (default `-80`) | −160…0 | dBm | LoRa link RSSI |
| `snr` | number | no (default `0`) | −40…40 | dB | LoRa signal-to-noise ratio |
| `timestamp` | ISO-8601 string / date | no (default now) | coercible date | — | Node capture time; coerced to UTC ISO |
| `packetId` | string | no | ≤100 chars | — | Firmware-generated idempotency/diagnostic id |

Unknown fields are **rejected** (`.strict()`). Numeric strings such as `"84"` are also rejected—convert in firmware before serializing.

### Response

```http
HTTP/1.1 202 Accepted
Content-Type: application/json
```

```json
{
  "ok": true,
  "accepted": 1,
  "ignored": 0,
  "nodes": [
    {
      "nodeId": "SN-NASH-01",
      "ignored": false,
      "riskLevel": "severe"
    }
  ],
  "evaluatedAt": "2026-10-26T14:32:01.114Z"
}
```

`ignored: true` means the reading was valid and retained for history but **not applied** to the node's live state because its `timestamp` is older than the node's last accepted reading. It is not an error. `packetId` is stored for diagnostics, not used for deduplication.

### Error example

```json
{
  "ok": false,
  "error": "Invalid payload",
  "issues": [
    { "path": "humidity", "message": "Number must be less than or equal to 100" },
    { "path": "waterLevel", "message": "Required" }
  ]
}
```

| Status | Meaning |
| --- | --- |
| `202` | Accepted (including ignored duplicates) |
| `400` | Schema validation failure |
| `401` | Missing/incorrect gateway key |
| `404` | Unknown node id |
| `429` | More than 120 telemetry requests/min from one IP (non-test) |

---

## 2. Batch reading (HTTP)

Use a batch when the gateway aggregates packets from multiple nodes.

```json
{
  "gatewayId": "GW-NSK-01",
  "firmware": "sentinel-gw 1.4.2",
  "timestamp": "2026-10-26T14:32:00.000Z",
  "readings": [
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
      "battery": 3.82
    },
    {
      "nodeId": "SN-NASH-02",
      "lat": 20.0234,
      "lon": 73.812,
      "temp": 27.1,
      "humidity": 91,
      "rain": 21.2,
      "waterLevel": 47.2,
      "vibration": 64,
      "aqi": 96,
      "sos": false,
      "battery": 3.79
    }
  ]
}
```

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `gatewayId` | string | **yes** | 3–64 chars; also accepted in the `X-Gateway-Id` header for single readings |
| `firmware` | string | no | ≤100 chars, stored in gateway diagnostics |
| `timestamp` | ISO-8601 | no | Envelope time; per-reading timestamps take precedence |
| `readings` | array | **yes** | 1–24 readings, each matching the single-reading schema |

### Batch response

```json
{
  "ok": true,
  "accepted": 2,
  "ignored": 0,
  "nodes": [
    { "nodeId": "SN-NASH-01", "ignored": false, "riskLevel": "severe" },
    { "nodeId": "SN-NASH-02", "ignored": false, "riskLevel": "high" }
  ],
  "evaluatedAt": "2026-10-26T14:32:01.114Z"
}
```

The whole batch is rejected if any one reading is invalid (atomic validation).

---

## 3. WebSocket ingestion

### Connect

```text
ws://localhost:5108/ws/gateway?key=gw-sentinel-demo-key
```

Authentication alternatives:

```http
X-Gateway-Key: gw-sentinel-demo-key
Authorization: Bearer gw-sentinel-demo-key
```

On connect the server sends:

```json
{
  "type": "gateway.ready",
  "gatewayId": "GW-NSK-01",
  "protocol": "sentinel.telemetry.v1",
  "serverTime": "2026-10-26T14:32:00.000Z"
}
```

### Send a single reading

Send the same object as the HTTP single-reading body. A response arrives immediately:

```json
{
  "type": "ack",
  "accepted": 1,
  "ignored": 0,
  "nodes": ["SN-NASH-01"],
  "serverTime": "2026-10-26T14:32:01.114Z"
}
```

### Send a batch

Two shapes are supported:

```json
{
  "type": "telemetry",
  "gatewayId": "GW-NSK-01",
  "firmware": "sentinel-gw 1.4.2",
  "readings": [ /* 1–24 readings */ ]
}
```

or the same batch object used for HTTP (no `type` wrapper). The ack reports node IDs.

### Error frame

```json
{ "type": "error", "message": "humidity: Number must be less than or equal to 100" }
```

The socket stays open after an error; fix and resend. Unauthorized upgrades are rejected with HTTP `401` before the WebSocket opens.

### Client keepalive

- Server sends WebSocket ping frames every 30 s and terminates dead peers.
- Application-level `{ "type": "ping" }` is optional; server responds with `pong`.
- Reconnect with exponential backoff on the gateway. Do not queue readings indefinitely—drop oldest unacknowledged packets after 10 minutes to bound flash/RAM use.

---

## 4. Snapshot frames (browser clients)

Browser clients connect to `/ws` with no authentication and receive a read-only snapshot:

```json
{
  "type": "snapshot",
  "data": {
    "meta": { "protocol": "sentinel.telemetry.v1", "operator": "Duty Officer M. Rao" },
    "nodes": [ /* node, latest reading, risk, health, trends */ ],
    "alerts": [ /* active + acknowledged */ ],
    "incidents": [ /* latest 8 for the overview */ ],
    "summary": { /* network and risk aggregation */ },
    "gateway": { /* link status */ },
    "system": { /* evacuation and siren state */ }
  }
}
```

A snapshot is also available over `GET /api/dashboard` for polling fallback. Field examples are best inspected live at `http://localhost:5108/api/dashboard`.

---

## 5. Alert and incident records

Alerts are created and maintained by `server/telemetry-service.js`:

| Alert field | Meaning |
| --- | --- |
| `id` | `ALT-…` stable identifier |
| `nodeId`, `nodeName` | Source node |
| `type` | `flood`, `landslide`, `air_quality`, `heat`, `sos` |
| `severity` | `low`, `moderate`, `high`, `severe` |
| `status` | `active`, `acknowledged`, `resolved` |
| `source` | `automated`, `operator`, `sensor`, `system`, `hardware`, `simulator` |
| `message` | Operator-facing explanation |
| `metadata` | Risk score, factors, AQI, GPS and other machine context |

Alert lifecycle:

1. A hazard at `high`/`severe` opens one alert per `(node, type)`. Repeated readings escalate severity but do not duplicate the alert.
2. Acknowledgment adds an audit incident and pins the operator identity; it does not silence the underlying hazard.
3. High/severe alerts auto-resolve only after **two consecutive** readings below the high threshold. Moderate/low alerts are not auto-resolved.
4. SOS always creates a severe alert; clearing it requires command action.

Incidents are append-only audit records:

```json
{
  "id": "inc_0648a28a7c63403c",
  "nodeId": "SN-NASH-02",
  "nodeName": "Panchavati Ridge",
  "type": "sensor",
  "severity": "severe",
  "title": "Landslide threshold crossed",
  "detail": "Rain infiltration 23.7 mm/h, Slope exposure 96 / 100. Composite risk index 77.3/100.",
  "source": "sensor",
  "status": "monitoring",
  "createdAt": "2026-10-26T15:07:13.501Z",
  "metadata": { "riskScore": 77.3, "factors": [] }
}
```

`type` values: `alert`, `sensor`, `sos`, `command`, `acknowledgement`, `gateway`, `evacuation`, `drill`.  
`status` values: `open`, `monitoring`, `acknowledged`, `resolved`.

---

## 6. Units and calibration checklist

| Measurement | Unit | Calibration before deployment |
| --- | --- | --- |
| Temperature / humidity | °C / %RH | Compare DHT22 against a reference; apply offset |
| Rain | mm/h | Tipping bucket: `mm per tip × tips per interval × 3600 / intervalSeconds` |
| Water level | cm | Mount height − ultrasonic distance; median-filter 5 samples |
| Vibration | 0–100 | Normalize SW-420 impulse count over a 1 s window (e.g. 20 impulses → 100) |
| AQI | index | MQ-135 requires ≥24 h burn-in and Rs/R0 calibration against a known reference |
| Battery | V | Use a 100 kΩ/100 kΩ divider; multiply ADC voltage by 2; account for ESP32 ADC nonlinearity |
| GPS | degrees | Reject fixes with fewer than 4 satellites or HDOP > 2.5; send `null` otherwise |
| RSSI / SNR | dBm / dB | Read from the LoRa library after each packet |

A reading without a GPS fix is still valid (`lat`/`lon` omitted), but the map will place the node at its commissioned coordinates from `server/site.js`.

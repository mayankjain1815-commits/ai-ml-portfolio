# ESP32 + LoRa integration guide

This guide explains how to take the reference sketches in [`../firmware/`](../firmware/) from breadboard to a live uplink into SENTINEL. It is written against the exact contracts in [`payload-schema.md`](payload-schema.md).

## 1. Architecture

```text
┌─────────────┐  LoRa 865–867 MHz  ┌──────────────┐  Wi-Fi/LAN   ┌──────────────┐
│ ESP32 Node   │ ──────────────────► │ ESP32 Gateway │ ───────────► │ SENTINEL API  │
│ (sensors)    │   JSON packets     │ (auth + batch) │  HTTP POST   │ :5108/api/v1  │
└─────────────┘                    └──────────────┘              │ /telemetry    │
                                                                     └──────────────┘
                                                                            │
                                                                            ▼
                                                                       SQLite + UI
```

- **Nodes** are offline. They have no Wi-Fi, no server URL, and no gateway key.
- **Gateway** receives LoRa frames, validates each reading, adds `rssi`, `snr` and an ISO UTC timestamp, de-duplicates by `packetId`, batches up to 24, and forwards to `/api/v1/telemetry` with `X-Gateway-Key`.
- **Server** validates with Zod, runs the risk engine, updates alerts/incidents, persists to SQLite, and broadcasts over WebSocket to the browser.

## 2. Bill of materials

### Per field node

| Part | Qty | Notes |
| --- | --- | --- |
| ESP32 DevKit V1 | 1 | 38-pin recommended |
| SX1276/RFM95W LoRa module (868/915/865) | 1 | Use 865–867 MHz for India |
| DHT22/AM2302 | 1 | Temperature/humidity |
| Tipping bucket rain gauge (reed switch) | 1 | Pulse output |
| HC-SR04 ultrasonic sensor | 1 | Water level (use level shifter on ECHO) |
| SW-420 vibration module | 1 | Digital output |
| MQ-135 gas sensor module | 1 | Needs burn-in + R0 calibration |
| NEO-6M GPS (optional) | 1 | If no GPS fix, node uses commissioned coords |
| Momentary NO pushbutton | 1 | SOS (wire to GND, use INPUT_PULLUP) |
| 18650 + TP4056 or regulated supply | 1 | See power notes |
| Resistors/capacitors, perfboard/enclosure | — | As needed |

### Sector gateway

| Part | Qty | Notes |
| --- | --- | --- |
| ESP32 DevKit V1 | 1 | Same as node |
| SX1276/RFM95W LoRa module | 1 | Same band/sync as nodes |
| 5V/USB or PoE adapter | 1 | Reliable power + LAN/Wi-Fi |
| Weatherproof enclosure + antenna | 1 | Gateway should see all nodes with good RSSI |

## 3. Wiring

All logic is 3.3 V. **Do not** connect HC-SR04 ECHO directly to ESP32.

### Node pin map (matches `sentinel-node.ino`)

| Component | Pin(s) | ESP32 | Notes |
| --- | --- | --- | --- |
| LoRa (SPI) | SCK/MISO/MOSI/NSS/RST/DIO0/VCC/GND | 18/19/23/5/14/26/3.3V/GND | Antenna required |
| DHT22 | DATA/VCC/GND | 4/3.3V/GND | 4.7–10 kΩ pull-up to 3.3 V |
| Rain gauge | SIG/VCC/GND | 27/3.3V/GND | Switch to GND on tip, `INPUT_PULLUP` |
| HC-SR04 | TRIG/ECHO/VCC/GND | 32 / 33 (via divider) / 5V/GND | Use 1k/2k divider or bidirectional level shifter |
| SW-420 | DO/VCC/GND | 25/3.3V/GND | Tune sensitivity pot on module |
| MQ-135 | AO/VCC/GND | 34/5V/GND | Input-only ADC pin. Heat draws ~150 mA. |
| SOS button | NO/GND | 13/GND | `INPUT_PULLUP` |
| Battery divider | MID/VCC/GND | 35/through divider/GND | 100k/100k typical. Keep < 5.5 V at ADC |
| Status LED | +/– | 2/GND | Built-in is fine |
| GPS (NEO-6M) | TX/RX/VCC/GND | 16/17/3.3–5V/GND | 9600 8N1 |

### Gateway pin map (matches `sentinel-gateway.ino`)

| Component | Pin(s) | ESP32 | Notes |
| --- | --- | --- | --- |
| LoRa (SPI) | SCK/MISO/MOSI/NSS/RST/DIO0/VCC/GND | 18/19/23/5/14/26/3.3V/GND | Same radio params as nodes |
| Status LED | +/– | 2/GND | Shows Wi-Fi/queue state |

Radio parameters used by both sketches:

| Setting | Value | Rationale |
| --- | --- | --- |
| Frequency | `866E6` | India 865–867 MHz |
| Sync Word | `0x12` | Private network |
| Spreading Factor | `9` | Range/airtime balance |
| Bandwidth | `125 kHz` | Common for this use case |
| Coding Rate | `4/5` | Good noise immunity |
| Preamble | `8` | Reliable sync |
| TX Power | `17 dBm` | Check local regulations |

## 4. Arduino IDE setup

1. **Boards**: `File → Preferences → Additional Boards Manager URLs` add `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`. Then `Tools → Board → Boards Manager` install `esp32` by Espressif.
2. **Libraries**: `Sketch → Include Library → Manage Libraries` install:
   - `LoRa` by Sandeep Mistry
   - `DHT sensor library` by Adafruit
   - `Adafruit Unified Sensor`
   - `ArduinoJson` by Benoit Blanchon (v7.x)
   - `TinyGPSPlus` by Mikal Hart
3. **Board config**: `ESP32 Dev Module`, `Upload Speed: 921600` (or 115200), `Flash Frequency: 80MHz`, `Port: <your serial port>`.
4. **Partition**: Default is fine for these sketches.

## 5. Commission nodes

Edit `firmware/sentinel-node/sentinel-node.ino` before flashing each physical node:

```cpp
#define NODE_ID          "SN-NASH-01"  // SN-NASH-01 | SN-NASH-02 | SN-NASH-03
#define SITE_LAT          19.9975f
#define SITE_LON          73.7898f
#define WATER_MOUNT_CM    200.0f       // cm from sensor to dry reference
```

Cross-check coordinates against [`server/site.js`](../server/site.js). The server expects these exact IDs.

### Calibrate in the field

| Sensor | Action |
| --- | --- |
| Rain | Count tips for a known volume/time. Adjust `RAIN_MM_PER_TIP`. |
| Water level | Measure with a staff gauge at low/mid/high. Tune `WATER_MOUNT_CM`. |
| MQ-135 | Run in clean air for ≥24 h. Compute `R0`. Set `MQ135_R0_KOHM`. See [`MQ135 calibration`](https://jayconsystems.com/blog/understanding-a-gas-sensor) notes. |
| Vibration | Observe baseline counts. Scale factor `pulses * 8` is a starting point—tune to your module. |
| Battery | Verify with a multimeter across the divider vs ADC reading. |
| GPS | Leave outdoors with clear sky. If fix acquired (`age < 10s`), GPS values are used; else commissioned coords are used. |

### Flash node

1. Wire USB to ESP32, select port/board.
2. Upload `sentinel-node.ino`.
3. Open Serial Monitor at 115200. Expect:
   ```
   [sentinel] node SN-NASH-01 booting
   [sentinel] ready
   [lora] sent {"nodeId":"SN-NASH-01", ... "packetId":"..."}
   ```
4. If LoRa init fails, the sketch retries 5x then restarts. Check wiring/antenna/power.

## 6. Provision the gateway

1. Copy the template:

```bash
cd firmware/sentinel-gateway
cp secrets.example.h secrets.h
```

2. Edit `secrets.h`:

```cpp
#define WIFI_SSID        "your-ssid"
#define WIFI_PASSWORD    "your-password"
#define SENTINEL_URL     "http://192.168.1.50:5108"  // or https://...
#define SENTINEL_GATEWAY_KEY "gw-sentinel-demo-key" // must match server
```

The server's key is in [`server/config.js`](../server/config.js) (default `gw-sentinel-demo-key`) and can be overridden via `.env` `GATEWAY_KEY`.

3. Upload `sentinel-gateway.ino`.
4. Serial Monitor 115200 should show:
   ```
   [wifi] connecting to ...
   [wifi] connected 192.168.1.123
   [ntp] sync requested
   [sentinel] gateway ready
   [batch] queued SN-NASH-01 (1/24)
   [http] flushed 1 readings (202)
   ```

### Gateway behavior

- **Buffering**: If Wi-Fi drops, readings stay in RAM (up to 24). On reconnect they flush every 10 s.
- **Deduplication**: Last 32 `packetId` values are tracked.
- **Validation**: Required numeric fields and `vibration` type are checked before queuing. Invalid packets are logged and dropped.
- **Retries**: `401/429/5xx` keep the batch for retry. Permanent `4xx` (except auth/rate limit) discards the batch to avoid blocking the queue.
- **Timing**: Gateway adds `rssi`/`snr` from LoRa and a UTC `timestamp` if the node omits one. NTP sync uses `pool.ntp.org`/`time.nist.gov`.

## 7. End-to-end testing

### Start SENTINEL

```bash
cd /Users/mayankjain/Documents/Default\ Project/08-sentinel-iot
npm install
npm run dev        # or npm start after build
```

API: `http://localhost:5108` | UI: `http://localhost:5109` (dev) or `http://localhost:5108` (prod)

### Verify ingestion

```bash
# Check health
curl -s http://localhost:5108/api/health | jq '{ok, nodes: .nodes, simulation}'

# Watch nodes update
watch -n 2 "curl -s http://localhost:5108/api/nodes | jq '.data[] | {id, online, lastSeen, risk: .risk.level, temp: .latest.temp, waterLevel: .latest.waterLevel}'"
```

### Send a manual test reading (bypass radios)

```bash
curl -X POST http://localhost:5108/api/v1/telemetry \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Key: gw-sentinel-demo-key" \
  -d '{
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
        "packetId": "MANUAL-001"
      }' | jq
```

Expected: `{"ok": true, "accepted": 1, "ignored": 0, ...}`

### Batch test

```bash
curl -X POST http://localhost:5108/api/v1/telemetry \
  -H "Content-Type: application/json" \
  -H "X-Gateway-Key: gw-sentinel-demo-key" \
  -d '{
        "gatewayId": "GW-NSK-01",
        "firmware": "sentinel-gw 1.5.0",
        "readings": [
          {"nodeId":"SN-NASH-01","lat":19.9975,"lon":73.7898,"temp":28.5,"humidity":93,"rain":25,"waterLevel":120,"vibration":10,"aqi":86,"sos":false,"battery":3.81},
          {"nodeId":"SN-NASH-02","lat":20.0234,"lon":73.812,"temp":27.2,"humidity":91,"rain":22,"waterLevel":48,"vibration":70,"aqi":98,"sos":false,"battery":3.78}
        ]
      }' | jq
```

### WebSocket test (gateway)

Using [`wscat`](https://github.com/websockets/wscat):

```bash
wscat -c "ws://localhost:5108/ws/gateway?key=gw-sentinel-demo-key"
```

Send a reading:
```json
{"nodeId":"SN-NASH-03","lat":20.0488,"lon":73.8425,"temp":33.4,"humidity":71,"rain":4.2,"waterLevel":24,"vibration":0,"aqi":187,"sos":false,"battery":4.06}
```

Expect:
```json
{"type":"gateway.ready", ...}
{"type":"ack", "accepted":1, "ignored":0, "nodes":["SN-NASH-03"], ...}
```

Browser clients connect to `ws://localhost:5108/ws` and receive `{"type":"snapshot", ...}` frames.

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Node never transmits | DHT returns NaN at boot | Wait 2–3 s after power; sketch retries and skips invalid climate reads. Check wiring/pull-up. |
| Gateway hears nothing | Frequency/sync/SF/BW/CRC mismatch | Match all radio params. Try different antenna orientation. Check 3.3 V supply. |
| `401 Invalid gateway key` | Key mismatch | Ensure `secrets.h` matches server `GATEWAY_KEY`. |
| `400 Invalid payload` | Schema violation | Check required fields, types. `vibration` must be boolean or number 0–100. Unknown fields rejected. |
| Node appears offline in UI | Last seen > 6 min | Check battery/RSSI. Gateway must forward packets. |
| Water level stuck at 0 | Ultrasonic timeout or mount height wrong | Verify ECHO divider, `WATER_MOUNT_CM`, and clear line of sight. |
| AQI seems high/low | No MQ-135 burn-in/R0 | Calibrate in clean air. Treat as AQI-equivalent unless replaced. |
| GPS coordinates ignored | Weak fix | Move antenna outside/window. If `age > 10s` or invalid, commissioned coords are used (this is expected indoors). |
| Queue grows, never flushes | Wi-Fi down / wrong URL | Check `SENTINEL_URL` reachable from gateway LAN. Test with curl from gateway subnet. |
| Duplicate ignored | Replayed `packetId` | Normal if retransmitting. Generate unique `packetId` per transmission. |

## 9. Power, enclosure & safety

- **Node power**: 18650 + TP4056 is common. Size for MQ-135 heater (~150 mA) + ESP32 (~80–120 mA) + radio TX (~120 mA peak). Budget realistically for overcast days.
- **Gateway power**: Use a quality 5V adapter. Keep on UPS if possible for 24/7 operation.
- **Enclosure**: IP65 for outdoor nodes. Use gland for cable entries, drip loop on antenna.
- **Antenna**: 1/4-wave 865 MHz, vertical polarization. Keep away from metal enclosures touching the radiating element.
- **Lightning**: For exposed river gauges consider gas discharge / surge protection on long sensor cables.
- **Safety**: If installing near water in monsoon, use appropriate PPE and follow local DDMA procedures.
- **Regulations**: Respect local RF power limits for ISM 865–867 MHz.

## 10. Quick reference

| Item | Value |
| --- | --- |
| HTTP ingest | `POST http://<server>:5108/api/v1/telemetry` |
| Gateway key header | `X-Gateway-Key: <GATEWAY_KEY>` |
| Gateway WS | `ws://<server>:5108/ws/gateway?key=<GATEWAY_KEY>` |
| Browser WS | `ws://<server>:5108/ws` |
| Node firmware | `firmware/sentinel-node/sentinel-node.ino` |
| Gateway firmware | `firmware/sentinel-gateway/sentinel-gateway.ino` |
| Schema | [`docs/payload-schema.md`](payload-schema.md) |
| Server config | [`server/config.js`](../server/config.js) |

**Tips for demo day:**

1. Flash all three nodes with their correct `NODE_ID`/coords.
2. Start gateway, confirm 202 responses in its serial log.
3. Open `http://localhost:5108` and watch Overview/Map/Alerts populate.
4. Trigger SOS on a node (hold button >600 ms) to show the severe alert flow.
5. Use the Command Console to acknowledge, override, or issue evacuation/all-clear.

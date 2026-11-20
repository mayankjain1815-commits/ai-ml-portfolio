# SENTINEL firmware

Two Arduino sketches implement the physical layer of the demo network.

```text
firmware/
├── sentinel-node/
│   └── sentinel-node.ino        ESP32 + sensors + LoRa transmitter
└── sentinel-gateway/
    ├── sentinel-gateway.ino     ESP32 + LoRa receiver + WiFi + HTTP uplink
    └── secrets.example.h        WiFi/server/key template (copy to secrets.h)
```

The node has **no WiFi and no credentials**. It only speaks LoRa. The gateway owns the authenticated HTTP connection to SENTINEL and can buffer packets while the network is down.

## 1. Libraries

Install through **Arduino IDE → Library Manager** (or `arduino-cli lib install`):

| Library | Version tested | Used by |
| --- | --- | --- |
| `LoRa` by Sandeep Mistry | 0.8.0 | node + gateway |
| `DHT sensor library` by Adafruit | 1.4.6 | node |
| `Adafruit Unified Sensor` | 1.1.14 | DHT dependency |
| `ArduinoJson` by Benoit Blanchon | 7.x | node + gateway |
| `TinyGPSPlus` by Mikal Hart | 1.0.3 | node (optional GPS) |

Board package: **esp32 by Espressif**, version 2.0.17 or newer. Select **ESP32 Dev Module**, 115200 baud.

## 2. Node wiring

| Device | Signal | ESP32 pin | Notes |
| --- | --- | --- | --- |
| SX1276 / RFM95W | SCK | GPIO18 | 3.3 V logic only |
| | MISO | GPIO19 | |
| | MOSI | GPIO23 | |
| | NSS | GPIO5 | |
| | RST | GPIO14 | |
| | DIO0 | GPIO26 | |
| | VCC / GND | 3.3 V / GND | Never 5 V |
| DHT22 | DATA | GPIO4 | 4.7–10 kΩ pull-up to 3.3 V |
| Tipping-bucket rain gauge | PULSE | GPIO27 | `INPUT_PULLUP`, switch to GND |
| HC-SR04 | TRIG | GPIO32 | 5 V sensor: use a divider on ECHO |
| | ECHO | GPIO33 | **3.3 V max at ESP32** |
| SW-420 vibration switch | DO | GPIO25 | `INPUT_PULLUP`; adjust onboard threshold |
| MQ-135 | AO | GPIO34 | Input-only ADC; 3.3 V supply |
| SOS button | — | GPIO13 → GND | `INPUT_PULLUP`, momentary |
| Battery divider | midpoint | GPIO35 | 100 kΩ / 100 kΩ; ADC input only |
| Status LED | — | GPIO2 | Onboard LED usually works |
| GPS NEO-6M (optional) | TX | GPIO16 | 9600 baud |
| | RX | GPIO17 | |
| | VCC / GND | 3.3–5 V / GND | Module dependent |

> **HC-SR04 ECHO is 5 V.** Use a 1 kΩ / 2 kΩ divider (or level shifter) before GPIO33. The MQ-135 heater draws ~150 mA; power it from a stable 5 V rail and level-shift its analog output, or use a 3.3 V-compatible module. Do not power the radio and heater from the ESP32 3.3 V regulator alone.

## 3. Commission the node

Open `sentinel-node/sentinel-node.ino` and set the four commissioning constants:

```cpp
#define NODE_ID          "SN-NASH-01"
#define SITE_LAT          19.9975f
#define SITE_LON          73.7898f
#define WATER_MOUNT_CM    200.0f
```

Use the registration values in `server/site.js`:

| Node | `SITE_LAT` | `SITE_LON` | Suggested mount |
| --- | --- | --- | --- |
| `SN-NASH-01` | `19.9975` | `73.7898` | 200 cm above dry river bed |
| `SN-NASH-02` | `20.0234` | `73.8120` | local slope datum |
| `SN-NASH-03` | `20.0488` | `73.8425` | reservoir spillway datum |

`WATER_MOUNT_CM` is the distance from the ultrasonic sensor face to the zero-water reference. The sketch computes `waterLevel = mount − median(distance)`, clamps to `0…1500 cm`, and rejects timeouts.

If a GPS fix exists, its coordinates replace the commissioned coordinates. If not, the commissioned pair is sent—so the map always has an exact node location.

## 4. Calibration

The firmware ships with conservative defaults. Field deployment **must** recalibrate:

1. **Rain gauge** — measure the bucket resolution (commonly `0.2794 mm/tip`) and update `RAIN_MM_PER_TIP`. Verify with a measured 10 mm pour.
2. **Water level** — measure the actual mount height, update `WATER_MOUNT_CM`, and cross-check against a staff gauge at three water stages.
3. **MQ-135** — burn in for ≥24 h in clean air, measure `Rs`, and set `MQ135_R0_KOHM`. The AQI conversion is an AQI-equivalent estimate derived from the sensor response curve, not a certified PM2.5 measurement. If regulatory AQI is required, use a dedicated PM2.5 sensor and replace `readAqi()`.
4. **Battery** — verify the divider ratio and use `analogReadMilliVolts` (already calibrated by the ESP32 core). A single 18650 cell maps 3.30 V → 0% and 4.20 V → 100%.
5. **Vibration** — the SW-420 pulse count is scaled to `0–100` over a 5-second window (`pulses × 8`, capped at 100). Tune after a week of baseline data.
6. **SOS** — the button must be held for 600 ms to latch. This rejects accidental bumps while remaining easy to use under stress.

## 5. Flash and verify

1. Connect the node over USB, select the correct port, and upload.
2. Open Serial Monitor at **115200**. You should see `[sentinel] ready`, then one `[lora] sent {...}` every 60 s.
3. Flash the gateway and open its Serial Monitor. You should see `[batch] queued SN-NASH-01` followed by `[http] flushed … (202)`.
4. Check the UI or API:

```bash
curl -s http://localhost:5108/api/nodes | jq '.data[] | {id, lastSeen, packetCount, risk: .risk.level}'
```

If the node never appears, the gateway is probably fine and the radio link is not. Verify frequency (`866E6`), sync word (`0x12`), spreading factor (`9`), bandwidth (`125 kHz`), coding rate (`4/5`), CRC, antenna, and power.

## 6. Gateway setup

```bash
cd firmware/sentinel-gateway
cp secrets.example.h secrets.h
$EDITOR secrets.h
```

Set:

```cpp
#define WIFI_SSID            "site-wifi"
#define WIFI_PASSWORD        "…"
#define SENTINEL_URL         "http://192.168.1.50:5108"
#define SENTINEL_GATEWAY_KEY "gw-sentinel-demo-key"
```

`SENTINEL_GATEWAY_KEY` must equal the server's `GATEWAY_KEY`. `SENTINEL_URL` must be reachable from the gateway WiFi network. For production use an HTTPS URL and add a `WiFiClientSecure` with the deployment CA—plain HTTP is only appropriate on an isolated control-room LAN.

The gateway:

- receives and JSON-decodes each LoRa packet;
- validates required fields before buffering;
- adds RSSI, SNR and a UTC timestamp;
- de-duplicates the last 32 `packetId` values;
- buffers up to 24 readings and flushes every 10 s;
- keeps buffered readings during WiFi outages and retries;
- drops a batch on permanent `4xx` validation errors, but retries `401`/`429`/`5xx`.

`secrets.h` is gitignored. Never commit real WiFi credentials or a production gateway key.

## 7. Power and enclosure notes

- The node is mains-independent only if powered from a solar/18650 pack. The MQ-135 heater is the dominant load; budget for it or duty-cycle the sensor.
- Use an IP65 enclosure, a drip loop on the antenna cable, and a desiccant pack.
- Keep the LoRa antenna clear of the water surface and metal structures. A 1/4-wave 866 MHz antenna is adequate for ~1–3 km line-of-sight.
- Add a fuse on the battery positive lead and reverse-polarity protection.
- Mount the ultrasonic sensor so its cone is not blocked by vegetation or debris. A stilling well improves river-level readings.
- Lightning protection / shielded cable is recommended for permanently installed river gauges.

## 8. Protocol reference

The exact JSON, field ranges, HTTP responses, WebSocket frames and lifecycle rules are in [`../docs/payload-schema.md`](../docs/payload-schema.md). Wiring, provisioning and troubleshooting are expanded in [`../docs/esp32-integration.md`](../docs/esp32-integration.md).

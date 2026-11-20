import assert from 'node:assert/strict';
import test from 'node:test';
import {
  commandSchemas,
  gatewayBatchSchema,
  telemetrySchema,
} from '../server/validation.js';
import { readingFor } from './helpers.js';

const sensorPayload = (nodeId = 'SN-NASH-01', overrides = {}) => {
  const { vibrationLevel, ...reading } = readingFor(nodeId, overrides);
  return reading;
};

test('telemetry accepts the documented ESP32 payload and normalizes vibration', () => {
  const parsed = telemetrySchema.parse({
    nodeId: 'SN-NASH-01',
    lat: 19.9975,
    lon: 73.7898,
    temp: 28.4,
    humidity: 92,
    rain: 24.2,
    waterLevel: 128,
    vibration: 72,
    aqi: 90,
    sos: false,
    battery: 3.82,
    rssi: -67,
    snr: 7.6,
  });

  assert.equal(parsed.nodeId, 'SN-NASH-01');
  assert.equal(parsed.vibration, true);
  assert.equal(parsed.vibrationLevel, 72);
  assert.equal(parsed.lat, 19.9975);
  assert.ok(!Number.isNaN(Date.parse(parsed.timestamp)));
  assert.equal(parsed.sos, false);
});

test('telemetry maps a boolean vibration contact to a 0/100 level', () => {
  const active = telemetrySchema.parse({ ...sensorPayload(), vibration: true });
  const idle = telemetrySchema.parse({ ...sensorPayload(), vibration: false });
  assert.equal(active.vibrationLevel, 100);
  assert.equal(active.vibration, true);
  assert.equal(idle.vibrationLevel, 0);
  assert.equal(idle.vibration, false);
});

test('telemetry allows missing coordinates but rejects out-of-range values', () => {
  const parsed = telemetrySchema.parse({
    nodeId: 'SN-NASH-01',
    temp: 28,
    humidity: 80,
    rain: 2,
    waterLevel: 20,
    vibration: false,
    aqi: 50,
    battery: 3.9,
  });
  assert.equal(parsed.lat, null);
  assert.equal(parsed.lon, null);

  assert.throws(() =>
    telemetrySchema.parse({
      ...sensorPayload(),
      battery: 9.2,
    }),
  );
  assert.throws(() =>
    telemetrySchema.parse({
      ...sensorPayload(),
      humidity: 140,
    }),
  );
  assert.throws(() =>
    telemetrySchema.parse({
      ...sensorPayload(),
      lat: 120,
    }),
  );
});

test('telemetry is strict about required fields and unknown firmware fields', () => {
  const { nodeId, ...missingNode } = sensorPayload();
  assert.throws(() => telemetrySchema.parse(missingNode));
  assert.throws(() => telemetrySchema.parse({ ...sensorPayload(), unsupportedField: true }));
  assert.throws(() => telemetrySchema.parse({ ...sensorPayload(), nodeId: 'ab' }));
});

test('gateway batches enforce a non-empty bounded reading array', () => {
  const batch = gatewayBatchSchema.parse({
    gatewayId: 'GW-NSK-01',
    firmware: 'sentinel-gw 1.4.2',
    readings: [sensorPayload('SN-NASH-01'), sensorPayload('SN-NASH-02')],
  });
  assert.equal(batch.readings.length, 2);

  assert.throws(() =>
    gatewayBatchSchema.parse({
      gatewayId: 'GW-NSK-01',
      readings: [],
    }),
  );

  assert.throws(() =>
    gatewayBatchSchema.parse({
      gatewayId: 'GW-NSK-01',
      readings: Array.from({ length: 25 }, () => sensorPayload()),
    }),
  );
});

test('command payloads validate operator and required rationale', () => {
  assert.equal(
    commandSchemas.override.parse({
      nodeId: 'SN-NASH-01',
      level: 'high',
      note: 'Visual confirmation of rising water.',
      durationMinutes: 60,
    }).durationMinutes,
    60,
  );

  assert.throws(() =>
    commandSchemas.override.parse({
      nodeId: 'SN-NASH-01',
      level: 'critical',
      note: 'Invalid level',
    }),
  );

  assert.throws(() =>
    commandSchemas.evacuation.parse({
      nodeId: 'SN-NASH-01',
      reason: 'tiny',
    }),
  );

  assert.throws(() => commandSchemas.siren.parse({ enabled: 'yes' }));
});

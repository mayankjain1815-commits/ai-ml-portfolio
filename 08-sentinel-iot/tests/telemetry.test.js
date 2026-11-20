import assert from 'node:assert/strict';
import test from 'node:test';
import { TelemetryService, UnknownNodeError } from '../server/telemetry-service.js';
import { createStore, readingFor } from './helpers.js';

const at = (offsetSeconds = 0) =>
  new Date(Date.now() + offsetSeconds * 1000).toISOString();

test('ingestion updates node state, packet count and assessed risk', () => {
  const store = createStore();
  const service = new TelemetryService(store);
  const reading = readingFor('SN-NASH-01', {
    timestamp: at(),
    waterLevel: 112,
    rain: 22,
    humidity: 94,
  });

  const result = service.ingest(reading, { gatewayId: 'GW-NSK-01', source: 'gateway-http' });

  assert.equal(result.accepted, true);
  assert.equal(result.ignored, false);
  assert.equal(result.nodeId, 'SN-NASH-01');
  assert.equal(result.risk.level, 'high');
  assert.equal(result.alerts.length, 1);
  assert.equal(result.alerts[0].type, 'flood');
  assert.equal(result.alerts[0].status, 'active');

  const node = store.getNode('SN-NASH-01');
  assert.equal(node.latest.waterLevel, 112);
  assert.equal(node.latest.rain, 22);
  assert.equal(node.packetCount, 1);
  assert.equal(node.risk.level, 'high');
  assert.ok(node.lastSeen);

  const gateway = store.getGateway('GW-NSK-01');
  assert.equal(gateway.packets, 1);
  assert.equal(gateway.status, 'online');
});

test('repeated dangerous readings deduplicate one active hazard alert', () => {
  const store = createStore();
  const service = new TelemetryService(store);

  const first = service.ingest(
    readingFor('SN-NASH-01', { timestamp: at(), waterLevel: 120, rain: 26, humidity: 95 }),
  );
  assert.equal(first.alerts.length, 1);
  const firstAlertId = first.alerts[0].id;

  const second = service.ingest(
    readingFor('SN-NASH-01', { timestamp: at(1), waterLevel: 130, rain: 28, humidity: 96 }),
  );
  assert.equal(second.alerts.length, 0);
  assert.equal(store.listAlerts().filter((alert) => alert.type === 'flood').length, 1);
  assert.equal(store.getAlert(firstAlertId).severity, 'severe');
});

test('escalating hazard severity updates the existing warning', () => {
  const store = createStore();
  const service = new TelemetryService(store);

  const first = service.ingest(
    readingFor('SN-NASH-01', { timestamp: at(), waterLevel: 100, rain: 15, humidity: 88 }),
  );
  assert.equal(first.risk.level, 'high');
  assert.equal(first.alerts[0].severity, 'high');

  const escalated = service.ingest(
    readingFor('SN-NASH-01', { timestamp: at(1), waterLevel: 132, rain: 30, humidity: 96 }),
  );
  assert.equal(escalated.risk.level, 'severe');
  assert.equal(escalated.alerts.length, 1);
  assert.equal(escalated.alerts[0].id, first.alerts[0].id);
  assert.equal(escalated.alerts[0].severity, 'severe');
  assert.equal(store.listAlerts({ includeResolved: true }).filter((a) => a.type === 'flood').length, 1);
});

test('a cleared hazard needs two sub-threshold packets before resolving', () => {
  const store = createStore();
  const service = new TelemetryService(store);

  const active = service.ingest(
    readingFor('SN-NASH-01', { timestamp: at(), waterLevel: 130, rain: 30, humidity: 96 }),
  );
  assert.equal(active.risk.level, 'severe');
  const alertId = active.alerts[0].id;

  const firstClear = service.ingest(
    readingFor('SN-NASH-01', {
      timestamp: at(1),
      waterLevel: 10,
      rain: 0,
      humidity: 55,
      temp: 24,
      aqi: 30,
      vibrationLevel: 0,
    }),
  );
  assert.equal(firstClear.risk.level, 'low');
  assert.equal(store.getAlert(alertId).status, 'active');

  const secondClear = service.ingest(
    readingFor('SN-NASH-01', {
      timestamp: at(2),
      waterLevel: 9,
      rain: 0,
      humidity: 54,
      temp: 24,
      aqi: 30,
      vibrationLevel: 0,
    }),
  );
  assert.equal(secondClear.risk.level, 'low');
  assert.equal(store.getAlert(alertId).status, 'resolved');

  const clearedIncident = store
    .listIncidents({ search: 'warning cleared', limit: 10 })
    .incidents.find((incident) => incident.metadata.alertId === alertId);
  assert.ok(clearedIncident);
});

test('manual SOS creates one severe alert until the signal clears', () => {
  const store = createStore();
  const service = new TelemetryService(store);

  const first = service.ingest(readingFor('SN-NASH-02', { timestamp: at(), sos: true }));
  const sosAlerts = first.alerts.filter((alert) => alert.type === 'sos');
  assert.equal(sosAlerts.length, 1);
  assert.equal(sosAlerts[0].severity, 'severe');
  assert.equal(first.risk.primaryHazard, 'sos');

  const second = service.ingest(readingFor('SN-NASH-02', { timestamp: at(1), sos: true }));
  assert.equal(second.alerts.filter((alert) => alert.type === 'sos').length, 0);
  assert.equal(store.listAlerts().filter((alert) => alert.type === 'sos').length, 1);
});

test('stale telemetry is stored but cannot overwrite a newer node state', () => {
  const store = createStore();
  const service = new TelemetryService(store);

  service.ingest(readingFor('SN-NASH-01', { timestamp: at(30), waterLevel: 44 }));
  const newer = store.getNode('SN-NASH-01');

  const stale = service.ingest(
    readingFor('SN-NASH-01', { timestamp: at(-30), waterLevel: 140, rain: 40 }),
  );

  assert.equal(stale.accepted, true);
  assert.equal(stale.ignored, true);
  assert.equal(stale.reason, 'stale_timestamp');
  assert.equal(store.getNode('SN-NASH-01').latest.waterLevel, newer.latest.waterLevel);
  assert.equal(store.getNode('SN-NASH-01').packetCount, newer.packetCount);
  assert.equal(store.getRecentTelemetry('SN-NASH-01', 10).length, 2);
});

test('batches report accepted and ignored readings and unknown nodes are rejected', () => {
  const store = createStore();
  const service = new TelemetryService(store);

  const result = service.ingestBatch(
    [
      readingFor('SN-NASH-01', { timestamp: at() }),
      readingFor('SN-NASH-02', { timestamp: at(1) }),
    ],
    { gatewayId: 'GW-NSK-01' },
  );
  assert.equal(result.accepted, 2);
  assert.equal(result.ignored, 0);

  assert.throws(
    () => service.ingest(readingFor('SN-UNKNOWN', { timestamp: at(2) })),
    (error) => error instanceof UnknownNodeError && error.status === 404,
  );
});

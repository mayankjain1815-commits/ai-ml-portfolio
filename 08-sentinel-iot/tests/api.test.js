import assert from 'node:assert/strict';
import test from 'node:test';
import request from 'supertest';
import { createApp } from '../server/app.js';
import { createStore } from './helpers.js';
import { generateToken } from '../server/middleware/auth.js';

const GATEWAY_KEY = 'gw-sentinel-demo-key';
// Tokens used to be hard-coded here with a one-hour expiry, so the suite
// started failing as soon as that timestamp passed. Sign one at run time.
const ADMIN_AUTH = {
  Authorization: `Bearer ${generateToken({ id: 1, username: 'admin', role: 'admin' })}`,
};

function makeApp(options = {}) {
  const store = createStore(options);
  const app = createApp({
    store,
    simulate: false,
    simulationStatus: () => ({ running: false }),
  });
  return { app, store };
}

async function authHeader(app) {
  const res = await request(app).post('/api/auth/login').send({ username: 'admin', password: 'admin' });
  if (res.body?.token) {
    return { Authorization: `Bearer ${res.body.token}` };
  }
  return {};
}

function documentedReading(overrides = {}) {
  return {
    nodeId: 'SN-NASH-01',
    lat: 19.9975,
    lon: 73.7898,
    temp: 28.4,
    humidity: 92,
    rain: 22,
    waterLevel: 118,
    vibration: 8,
    aqi: 84,
    sos: false,
    battery: 3.82,
    rssi: -67,
    snr: 7.6,
    ...overrides,
  };
}

test('health and dashboard endpoints expose a complete operational snapshot', async () => {
  const { app } = makeApp({ seed: true });

  const health = await request(app).get('/api/health').expect(200);
  assert.equal(health.body.ok, true);
  assert.equal(health.body.service, 'sentinel-iot-command');
  assert.equal(health.body.nodes.total, 3);
  assert.equal(health.body.database, 'memory');

  const dashboard = await request(app).get('/api/dashboard').expect(200);
  const data = dashboard.body.data;
  assert.equal(dashboard.body.ok, true);
  assert.equal(data.nodes.length, 3);
  assert.equal(data.summary.nodesTotal, 3);
  assert.equal(data.summary.nodesOnline, 3);
  assert.deepEqual(data.summary.riskDistribution, {
    low: 0,
    moderate: 1,
    high: 1,
    severe: 1,
  });
  assert.ok(data.alerts.length >= 3);
  assert.ok(data.incidents.length > 0);
  assert.ok(data.nodes.every((node) => node.risk && node.health && Array.isArray(node.trends.water)));
  assert.ok(data.meta.site.code === 'SECTOR-04');
  assert.equal(data.system.evacuation.active, false);
  assert.equal(data.gateway.online, true);
});

test('node history returns the last six hours and rejects unknown nodes', async () => {
  const { app } = makeApp({ seed: true });

  const history = await request(app).get('/api/nodes/SN-NASH-01/history?hours=6').expect(200);
  assert.equal(history.body.data.node.id, 'SN-NASH-01');
  assert.ok(history.body.data.history.length > 10);
  assert.ok(history.body.data.history.every((point) => point.nodeId === 'SN-NASH-01'));

  await request(app).get('/api/nodes/SN-MISSING').expect(404);
  await request(app).get('/api/nodes/SN-MISSING/history').expect(404);
});

test('telemetry ingress requires the gateway key and validates the payload', async () => {
  const { app, store } = makeApp();

  await request(app).post('/api/v1/telemetry').send(documentedReading()).expect(401);
  await request(app)
    .post('/api/v1/telemetry')
    .set('x-gateway-key', 'wrong-key')
    .send(documentedReading())
    .expect(401);
  await request(app)
    .post('/api/v1/telemetry')
    .set('x-gateway-key', GATEWAY_KEY)
    .send({ nodeId: 'SN-NASH-01' })
    .expect(400);
  await request(app)
    .post('/api/v1/telemetry')
    .set('x-gateway-key', GATEWAY_KEY)
    .send(documentedReading({ battery: 22 }))
    .expect(400);
  await request(app)
    .post('/api/v1/telemetry')
    .set('x-gateway-key', GATEWAY_KEY)
    .send(documentedReading({ nodeId: 'SN-UNKNOWN' }))
    .expect(404);

  const accepted = await request(app)
    .post('/api/v1/telemetry')
    .set('x-gateway-key', GATEWAY_KEY)
    .set('x-gateway-id', 'GW-NSK-01')
    .send(documentedReading({ timestamp: new Date().toISOString() }))
    .expect(202);

  assert.equal(accepted.body.accepted, 1);
  assert.equal(accepted.body.ignored, 0);
  assert.equal(store.getNode('SN-NASH-01').latest.waterLevel, 118);
  assert.equal(store.getNode('SN-NASH-01').risk.level, 'severe');
  assert.ok(store.listAlerts().some((alert) => alert.type === 'flood'));
});

test('gateway batches accept multiple nodes in a single request', async () => {
  const { app, store } = makeApp();

  const response = await request(app)
    .post('/api/v1/telemetry')
    .set('x-gateway-key', GATEWAY_KEY)
    .send({
      gatewayId: 'GW-NSK-01',
      firmware: 'sentinel-gw 1.4.2',
      readings: [
        documentedReading({ timestamp: new Date(Date.now() + 1000).toISOString() }),
        documentedReading({ nodeId: 'SN-NASH-02', timestamp: new Date(Date.now() + 2000).toISOString() }),
        documentedReading({ nodeId: 'SN-NASH-03', timestamp: new Date(Date.now() + 3000).toISOString() }),
      ],
    })
    .expect(202);

  assert.equal(response.body.accepted, 3);
  assert.equal(response.body.ignored, 0);
  assert.equal(response.body.nodes.length, 3);
  assert.equal(store.getNode('SN-NASH-02').packetCount, 1);
  assert.equal(store.getNode('SN-NASH-03').packetCount, 1);
});

test('incident log supports search, filters, pagination and CSV export', async () => {
  const { app } = makeApp({ seed: true });

  const firstPage = await request(app).get('/api/incidents?limit=5&offset=0').expect(200);
  assert.equal(firstPage.body.incidents.length, 5);
  assert.ok(firstPage.body.total > 10);
  assert.equal(firstPage.body.limit, 5);
  assert.equal(firstPage.body.offset, 0);

  const search = await request(app).get('/api/incidents?search=Godavari&limit=50').expect(200);
  assert.ok(search.body.incidents.length > 0);
  assert.ok(
    search.body.incidents.every((incident) =>
      `${incident.title} ${incident.detail} ${incident.nodeName}`.includes('Godavari'),
    ),
  );

  const severe = await request(app).get('/api/incidents?severity=severe&limit=50').expect(200);
  assert.ok(severe.body.incidents.every((incident) => incident.severity === 'severe'));

  const sensor = await request(app).get('/api/incidents?type=sensor&limit=50').expect(200);
  assert.ok(sensor.body.incidents.every((incident) => incident.type === 'sensor'));

  const resolved = await request(app).get('/api/incidents?status=resolved&limit=50').expect(200);
  assert.ok(resolved.body.incidents.every((incident) => incident.status === 'resolved'));

  const stats = await request(app).get('/api/incidents/stats').expect(200);
  assert.ok(stats.body.data.severe >= 1);
  assert.ok(stats.body.data.high >= 1);

  const csv = await request(app).get('/api/incidents/export.csv?severity=severe').expect(200);
  assert.match(csv.headers['content-type'], /text\/csv/);
  assert.match(csv.headers['content-disposition'], /sentinel-incidents\.csv/);
  assert.match(csv.text, /Timestamp/);
  assert.match(csv.text, /Severity/);
  csv.text
    .trim()
    .split('\n')
    .slice(1)
    .forEach((row) => assert.match(row, /"severe"/));
});

test('alert acknowledgment records ownership and rejects repeat claims', async () => {
  const { app, store } = makeApp({ seed: true });

  const acknowledged = await request(app)
    .post('/api/alerts/ALT-SEED-FLOOD/acknowledge')
    .set(ADMIN_AUTH)
    .set('x-operator-name', 'Officer K. Patil')
    .send({})
    .expect(200);

  assert.equal(acknowledged.body.data.status, 'acknowledged');
  assert.equal(acknowledged.body.data.acknowledgedBy, 'Officer K. Patil');
  assert.ok(store.getAlert('ALT-SEED-FLOOD').acknowledgedAt);

  await request(app)
    .post('/api/alerts/ALT-SEED-FLOOD/acknowledge')
    .set(ADMIN_AUTH)
    .send({ operator: 'Officer K. Patil' })
    .expect(409);
  await request(app).post('/api/alerts/ALT-MISSING/acknowledge').set(ADMIN_AUTH).send({}).expect(404);

  const incident = store
    .listIncidents({ search: 'acknowledged', limit: 20 })
    .incidents.find((item) => item.metadata.alertId === 'ALT-SEED-FLOOD');
  assert.ok(incident);
});

test('bulk acknowledgment clears only unacknowledged alerts', async () => {
  const { app, store } = makeApp({ seed: true });

  const response = await request(app)
    .post('/api/alerts/acknowledge-all')
    .send({ operator: 'Officer K. Patil' })
    .expect(200);
  assert.equal(response.body.acknowledged, 2);
  assert.equal(store.listAlerts().filter((alert) => alert.status === 'active').length, 0);
  assert.ok(store.listAlerts().every((alert) => alert.status === 'acknowledged'));

  const again = await request(app).post('/api/alerts/acknowledge-all').set(ADMIN_AUTH).send({}).expect(200);
  assert.equal(again.body.acknowledged, 0);
});

test('risk overrides temporarily supersede the sensor assessment and can be removed', async () => {
  const { app, store } = makeApp({ seed: true });

  const applied = await request(app)
    .post('/api/commands/override')
    .set('x-operator-name', 'Officer K. Patil')
    .send({
      nodeId: 'SN-NASH-01',
      level: 'low',
      note: 'River gauge recalibrated, holding observation.',
      durationMinutes: 30,
    })
    .expect(200);

  assert.equal(applied.body.data.node.override.level, 'low');
  assert.equal(applied.body.data.node.override.by, 'Officer K. Patil');
  assert.ok(new Date(applied.body.data.node.override.until) > new Date());

  const dashboard = await request(app).get('/api/dashboard').expect(200);
  const node = dashboard.body.data.nodes.find((item) => item.id === 'SN-NASH-01');
  assert.equal(node.risk.level, 'low');
  assert.equal(node.risk.overridden, true);
  assert.equal(node.sensorRisk.level, 'severe');
  assert.equal(dashboard.body.data.summary.riskDistribution.low, 1);

  await request(app)
    .post('/api/commands/override')
    .send({ nodeId: 'SN-NASH-01', level: 'low', note: 'x' })
    .expect(400);
  await request(app)
    .post('/api/commands/override')
    .send({ nodeId: 'SN-MISSING', level: 'low', note: 'Valid rationale' })
    .expect(404);

  const cleared = await request(app)
    .delete('/api/nodes/SN-NASH-01/override')
    .set('x-operator-name', 'Officer K. Patil')
    .expect(200);
  assert.equal(cleared.body.data.node.override, null);
  assert.equal(store.getNode('SN-NASH-01').risk.level, 'severe');

  await request(app).delete('/api/nodes/SN-NASH-01/override').expect(409);
});

test('evacuation orders raise an alert and all-clear returns the sector to monitoring', async () => {
  const { app, store } = makeApp({ seed: true });

  const issued = await request(app)
    .post('/api/commands/evacuation')
    .set('x-operator-name', 'Officer K. Patil')
    .send({ nodeId: null, reason: 'Godavari has crossed the severe flood stage.' })
    .expect(201);

  assert.equal(issued.body.data.state.active, true);
  assert.equal(issued.body.data.state.scope, 'all');
  assert.equal(issued.body.data.alert.type, 'evacuation');
  assert.equal(issued.body.data.alert.severity, 'severe');

  let dashboard = await request(app).get('/api/dashboard').expect(200);
  assert.equal(dashboard.body.data.summary.evacuationActive, true);
  assert.equal(dashboard.body.data.system.siren.enabled, true);
  assert.ok(dashboard.body.data.alerts.some((alert) => alert.type === 'evacuation'));

  await request(app)
    .post('/api/commands/evacuation')
    .send({ reason: 'Duplicate order attempt.' })
    .expect(409);

  const cleared = await request(app)
    .post('/api/commands/all-clear')
    .send({ operator: 'Officer K. Patil' })
    .expect(200);
  assert.equal(cleared.body.data.state.active, false);

  dashboard = await request(app).get('/api/dashboard').expect(200);
  assert.equal(dashboard.body.data.summary.evacuationActive, false);
  assert.equal(dashboard.body.data.system.siren.enabled, false);
  assert.ok(
    dashboard.body.data.alerts.every((alert) => alert.type !== 'evacuation' || alert.status === 'resolved'),
  );
  assert.ok(store.listAlerts({ includeResolved: true }).some((alert) => alert.type === 'evacuation' && alert.status === 'resolved'));

  await request(app).post('/api/commands/all-clear').send({}).expect(409);
});

test('evacuation can target one node and rejects unknown targets', async () => {
  const first = makeApp({ seed: true });

  await request(first.app)
    .post('/api/commands/evacuation')
    .set(ADMIN_AUTH)
    .send({ nodeId: 'SN-MISSING', reason: 'Unknown node evacuation.' })
    .expect(404);

  const issued = await request(first.app)
    .post('/api/commands/evacuation')
    .set(ADMIN_AUTH)
    .send({ nodeId: 'SN-NASH-01', reason: 'Localized riverside evacuation required.' })
    .expect(201);
  assert.equal(issued.body.data.state.scope, 'SN-NASH-01');
  assert.equal(issued.body.data.state.targetName, 'Godavari Ghat');
});

test('SOS exercise creates a severe alert and cannot duplicate an active SOS', async () => {
  const { app, store } = makeApp({ seed: true });

  const sos = await request(app)
    .post('/api/commands/test-sos')
    .set(ADMIN_AUTH)
    .set('x-operator-name', 'Officer K. Patil')
    .send({ nodeId: 'SN-NASH-02' })
    .expect(201);

  assert.equal(sos.body.data.alert.type, 'sos');
  assert.equal(sos.body.data.alert.severity, 'severe');
  assert.equal(sos.body.data.alert.metadata.drill, true);
  assert.ok(store.listAlerts().some((alert) => alert.type === 'sos' && alert.status === 'active'));

  await request(app)
    .post('/api/commands/test-sos')
    .set(ADMIN_AUTH)
    .send({ nodeId: 'SN-NASH-02' })
    .expect(409);
  await request(app)
    .post('/api/commands/test-sos')
    .set(ADMIN_AUTH)
    .send({ nodeId: 'SN-MISSING' })
    .expect(404);
});

test('siren control is persisted and audited', async () => {
  const { app, store } = makeApp({ seed: true });
  const login = await request(app).post('/api/auth/login').send({ username: 'admin', password: 'admin' });
  const auth = login.body?.token ? { Authorization: `Bearer ${login.body.token}` } : {};

  const enabled = await request(app)
    .post('/api/commands/siren')
    .set(auth)
    .set('x-operator-name', 'Officer K. Patil')
    .send({ enabled: true })
    .expect(200);
  assert.equal(enabled.body.data.enabled, true);
  assert.equal(store.getState('siren').enabled, true);

  const silenced = await request(app)
    .post('/api/commands/siren')
    .set(auth)
    .send({ enabled: false })
    .expect(200);
  assert.equal(silenced.body.data.enabled, false);
  assert.equal(store.getState('siren').enabled, false);

  await request(app).post('/api/commands/siren').set(auth).send({ enabled: 'yes' }).expect(400);
});

test('alerts can be filtered and resolved records are hidden by default', async () => {
  const { app, store } = makeApp({ seed: true });

  const active = await request(app).get('/api/alerts?status=active').expect(200);
  assert.ok(active.body.data.every((alert) => alert.status === 'active'));

  const acknowledged = await request(app).get('/api/alerts?status=acknowledged').expect(200);
  assert.ok(acknowledged.body.data.every((alert) => alert.status === 'acknowledged'));

  const all = await request(app).get('/api/alerts?status=all').expect(200);
  assert.ok(all.body.data.length >= 3);
  assert.ok(all.body.data.every((alert) => alert.status !== 'resolved'));

  store.resolveAlert('ALT-SEED-FLOOD');
  const defaultList = await request(app).get('/api/alerts').expect(200);
  assert.ok(defaultList.body.data.every((alert) => alert.id !== 'ALT-SEED-FLOOD'));
});

test('unknown API routes return a structured 404', async () => {
  const { app } = makeApp({ seed: true });
  const response = await request(app).get('/api/does-not-exist').expect(404);
  assert.equal(response.body.ok, false);
  assert.match(response.body.error, /Unknown API route/);
});

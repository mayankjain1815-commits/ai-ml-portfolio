import { assessRisk } from './risk-engine.js';
import { GATEWAY, NODES, NODE_SEED_PROFILE, SITE } from './site.js';
import { seededRandom } from './utils.js';

const minutesAgo = (minutes) => new Date(Date.now() - minutes * 60 * 1000).toISOString();

function interpolate(start, end, ratio) {
  return start + (end - start) * ratio;
}

function buildReading(node, profile, index, total, random) {
  const ratio = index / (total - 1);
  const easing = ratio * ratio * (3 - 2 * ratio);
  const jitter = (scale) => (random() - 0.5) * scale;

  return {
    nodeId: node.id,
    timestamp: new Date(Date.now() - (total - 1 - index) * 10 * 60 * 1000).toISOString(),
    lat: node.lat,
    lon: node.lon,
    temp: Math.round((interpolate(profile.start.temp, profile.end.temp, easing) + jitter(0.35)) * 10) / 10,
    humidity: Math.round(interpolate(profile.start.humidity, profile.end.humidity, easing) + jitter(2)),
    rain: Math.max(0, Math.round((interpolate(profile.start.rain, profile.end.rain, easing) + jitter(1.8)) * 10) / 10),
    waterLevel:
      Math.round((interpolate(profile.start.waterLevel, profile.end.waterLevel, easing) + jitter(2.4)) * 10) / 10,
    vibrationLevel:
      node.id === 'SN-NASH-02'
        ? index > total * 0.82
          ? Math.round(35 + random() * 20)
          : Math.round(random() * 12)
        : 0,
    aqi: Math.round(interpolate(profile.start.aqi, profile.end.aqi, easing) + jitter(7)),
    sos: false,
    battery: Math.round((interpolate(profile.start.battery, profile.end.battery, easing) + jitter(0.01)) * 100) / 100,
    rssi: Math.round(-62 - random() * 24),
    snr: Math.round((7 + random() * 4) * 10) / 10,
    packetId: `SEED-${node.id}-${String(index).padStart(3, '0')}`,
  };
}

function seedTelemetryHistory(store, random) {
  for (const node of NODES) {
    const profile = NODE_SEED_PROFILE[node.id];
    let previousWaterLevel = profile.start.waterLevel;
    const total = 37;

    for (let index = 0; index < total; index += 1) {
      const reading = buildReading(node, profile, index, total, random);
      const assessment = assessRisk(reading, {
        terrain: node.terrain,
        slopeRisk: node.slopeRisk,
        previousWaterLevel,
      });
      store.insertTelemetry(node.id, reading);
      store.updateNodeReading(node.id, reading, assessment);
      previousWaterLevel = reading.waterLevel;
    }
  }
}

function seedAlerts(store) {
  const nodeOne = store.getNode('SN-NASH-01');
  const nodeTwo = store.getNode('SN-NASH-02');
  const nodeThree = store.getNode('SN-NASH-03');

  const floodAlert = store.createAlert({
    id: 'ALT-SEED-FLOOD',
    nodeId: nodeOne.id,
    nodeName: nodeOne.name,
    type: 'flood',
    severity: 'severe',
    title: 'Severe flood warning — Godavari Ghat',
    message:
      `Water depth reached ${nodeOne.latest.waterLevel.toFixed(0)} cm with ${nodeOne.latest.rain.toFixed(1)} mm/h rainfall. ` +
      'Low-lying riverside settlements must prepare for immediate evacuation.',
    status: 'active',
    source: 'automated',
    createdAt: minutesAgo(12),
    metadata: { riskScore: nodeOne.risk.score, factors: nodeOne.risk.topFactors },
  });

  const landslideAlert = store.createAlert({
    id: 'ALT-SEED-SLOPE',
    nodeId: nodeTwo.id,
    nodeName: nodeTwo.name,
    type: 'landslide',
    severity: nodeTwo.risk.level,
    title: 'Landslide watch — Panchavati Ridge',
    message:
      `Slope saturation is critical after ${nodeTwo.latest.rain.toFixed(1)} mm/h rainfall. ` +
      'Ground vibration sensors have registered slope movement.',
    status: 'active',
    source: 'automated',
    createdAt: minutesAgo(7),
    metadata: { riskScore: nodeTwo.risk.score, factors: nodeTwo.risk.topFactors },
  });

  const airAlert = store.createAlert({
    id: 'ALT-SEED-AIR',
    nodeId: nodeThree.id,
    nodeName: nodeThree.name,
    type: 'air_quality',
    severity: 'moderate',
    title: 'Air quality advisory — Darna Spillway',
    message: 'AQI is elevated near the reservoir service road. Sensitive groups should limit outdoor exposure.',
    status: 'acknowledged',
    source: 'automated',
    createdAt: minutesAgo(42),
    acknowledgedAt: minutesAgo(31),
    acknowledgedBy: 'Duty Officer M. Rao',
    metadata: { aqi: nodeThree.latest.aqi },
  });

  return { floodAlert, landslideAlert, airAlert };
}

function seedIncidents(store, alerts) {
  const incidents = [
    {
      nodeId: 'SN-NASH-01',
      nodeName: 'Godavari Ghat',
      type: 'alert',
      severity: 'severe',
      title: 'Flood warning elevated to SEVERE',
      detail: 'Automated risk engine crossed the 75-point threshold. Water depth 128 cm, rainfall 26.2 mm/h.',
      source: 'automated',
      status: 'open',
      createdAt: minutesAgo(12),
      metadata: { alertId: alerts.floodAlert.id },
    },
    {
      nodeId: 'SN-NASH-01',
      nodeName: 'Godavari Ghat',
      type: 'sensor',
      severity: 'high',
      title: 'River gauge exceeded 120 cm',
      detail: 'HC-SR04 ultrasonic range crossed the severe flood stage. Packet SN-12842 accepted by gateway.',
      source: 'sensor',
      status: 'monitoring',
      createdAt: minutesAgo(18),
      metadata: { waterLevel: 121.8 },
    },
    {
      nodeId: 'SN-NASH-02',
      nodeName: 'Panchavati Ridge',
      type: 'alert',
      severity: 'high',
      title: 'Landslide watch issued',
      detail: 'SW-420 vibration impulse and saturated slope conditions combined above the high-risk threshold.',
      source: 'automated',
      status: 'open',
      createdAt: minutesAgo(7),
      metadata: { alertId: alerts.landslideAlert.id },
    },
    {
      nodeId: 'SN-NASH-02',
      nodeName: 'Panchavati Ridge',
      type: 'sensor',
      severity: 'high',
      title: 'Ground vibration burst detected',
      detail: '3 vibration impulses recorded in 10 seconds. Slope movement confidence 87%.',
      source: 'sensor',
      status: 'monitoring',
      createdAt: minutesAgo(9),
      metadata: { impulses: 3 },
    },
    {
      nodeId: 'SN-NASH-01',
      nodeName: 'Godavari Ghat',
      type: 'gateway',
      severity: 'low',
      title: 'LoRa gateway link healthy',
      detail: 'GW-NSK-01 acknowledged 12 packets across three nodes. RSSI within operating range.',
      source: 'system',
      status: 'resolved',
      createdAt: minutesAgo(24),
      metadata: { packets: 12 },
    },
    {
      nodeId: 'SN-NASH-03',
      nodeName: 'Darna Spillway',
      type: 'alert',
      severity: 'moderate',
      title: 'Air quality advisory acknowledged',
      detail: 'Duty Officer M. Rao acknowledged the advisory for Darna Spillway at 09:17.',
      source: 'operator',
      status: 'acknowledged',
      createdAt: minutesAgo(31),
      metadata: { alertId: alerts.airAlert.id },
    },
    {
      nodeId: 'SN-NASH-03',
      nodeName: 'Darna Spillway',
      type: 'sensor',
      severity: 'moderate',
      title: 'AQI trending upward',
      detail: 'MQ-135 smoke sensor rose from 142 to 187 within two hours. No open flame detected nearby.',
      source: 'sensor',
      status: 'monitoring',
      createdAt: minutesAgo(36),
      metadata: { aqi: 187 },
    },
    {
      nodeId: 'SN-NASH-02',
      nodeName: 'Panchavati Ridge',
      type: 'sos',
      severity: 'severe',
      title: 'Manual SOS test completed',
      detail: 'Field operator held the tactile SOS button for 3 seconds. Alert delivered to command console in 1.2 s.',
      source: 'hardware',
      status: 'resolved',
      createdAt: minutesAgo(196),
      metadata: { drill: true, battery: 3.86 },
    },
    {
      nodeId: 'SN-NASH-01',
      nodeName: 'Godavari Ghat',
      type: 'command',
      severity: 'moderate',
      title: 'Evacuation readiness check',
      detail: 'Siren channel tested across two riverside wards. No public broadcast was issued.',
      source: 'operator',
      status: 'resolved',
      createdAt: minutesAgo(221),
      metadata: {},
    },
    {
      nodeId: null,
      nodeName: 'Central gateway',
      type: 'gateway',
      severity: 'low',
      title: 'Gateway reconnected after power blip',
      detail: 'GW-NSK-01 restored uplink over 4G backup. All three nodes re-registered automatically.',
      source: 'system',
      status: 'resolved',
      createdAt: minutesAgo(282),
      metadata: { downtimeSeconds: 18 },
    },
    {
      nodeId: 'SN-NASH-03',
      nodeName: 'Darna Spillway',
      type: 'drill',
      severity: 'low',
      title: 'Reservoir telemetry drill',
      detail: 'Scheduled end-to-end test of the Darna spillway sensor and evacuation routing. All checks passed.',
      source: 'operator',
      status: 'resolved',
      createdAt: minutesAgo(340),
      metadata: {},
    },
    {
      nodeId: 'SN-NASH-01',
      nodeName: 'Godavari Ghat',
      type: 'sensor',
      severity: 'moderate',
      title: 'Rainfall rate crossed 15 mm/h',
      detail: 'LM393 raindrop sensor confirmed sustained monsoon rainfall. River gauge began rising.',
      source: 'sensor',
      status: 'resolved',
      createdAt: minutesAgo(418),
      metadata: { rain: 16.4 },
    },
  ];

  incidents.forEach((incident) => store.addIncident(incident));
}

export function seedDemoData(store) {
  if (store.listNodes().length > 0) {
    return false;
  }

  const random = seededRandom(20261026);
  store.transaction(() => {
    NODES.forEach((node) => store.insertNode(node));
    seedTelemetryHistory(store, random);
    store.upsertGateway(GATEWAY.id, {
      packets: 111,
      rssi: -71,
      firmware: GATEWAY.firmware,
      status: 'online',
    });
    store.setState('evacuation', {
      active: false,
      scope: null,
      reason: null,
      issuedAt: null,
      issuedBy: null,
    });
    store.setState('siren', { enabled: false });
    store.setState('site', SITE);
  });

  const alerts = seedAlerts(store);
  seedIncidents(store, alerts);
  return true;
}

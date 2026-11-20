import { SentinelStore } from '../server/store.js';
import { NODES, GATEWAY, SITE } from '../server/site.js';
import { seedDemoData } from '../server/seed.js';

export function createStore({ seed = false } = {}) {
  const store = new SentinelStore(':memory:');
  if (seed) {
    seedDemoData(store);
    return store;
  }

  NODES.forEach((node) => store.insertNode(node));
  store.upsertGateway(GATEWAY.id, {
    packets: 0,
    rssi: -70,
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
  return store;
}

export function readingFor(nodeId = 'SN-NASH-01', overrides = {}) {
  const node = NODES.find((item) => item.id === nodeId) ?? {
    lat: 19.9975,
    lon: 73.7898,
  };
  return {
    nodeId,
    timestamp: new Date().toISOString(),
    lat: node.lat,
    lon: node.lon,
    temp: 28.4,
    humidity: 92,
    rain: 4,
    waterLevel: 32,
    vibration: false,
    vibrationLevel: 0,
    aqi: 76,
    sos: false,
    battery: 3.86,
    rssi: -74,
    snr: 7.2,
    packetId: `TEST-${nodeId}-${Date.now()}`,
    ...overrides,
  };
}

export function weatherReading(overrides = {}) {
  return {
    temp: 28.4,
    humidity: 92,
    rain: 4,
    waterLevel: 32,
    vibration: false,
    vibrationLevel: 0,
    aqi: 76,
    sos: false,
    ...overrides,
  };
}

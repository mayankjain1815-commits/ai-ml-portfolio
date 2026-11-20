import { assessRisk } from './risk-engine.js';
import { GATEWAY } from './site.js';
import { seededRandom } from './utils.js';
import { getSectorNodes } from './sector-data.js';
import { getSector } from './sectors.js';

const minutesAgo = (minutes) => new Date(Date.now() - minutes * 60 * 1000).toISOString();

function interpolate(start, end, ratio) {
  return start + (end - start) * ratio;
}

function buildReading(node, profile, index, total, random) {
  const ratio = index / (total - 1);
  const easing = ratio * ratio * (3 - 2 * ratio);
  const jitter = (scale) => (random() - 0.5) * scale;

  const start = profile.start || { temp: 28, humidity: 72, rain: 4, waterLevel: 38, aqi: 82, battery: 0.92 };
  const end = profile.end || { temp: 32, humidity: 84, rain: 18, waterLevel: 96, aqi: 148, battery: 0.88 };

  return {
    nodeId: node.id,
    timestamp: new Date(Date.now() - (total - 1 - index) * 10 * 60 * 1000).toISOString(),
    lat: node.lat,
    lon: node.lon,
    temp: Math.round((interpolate(start.temp, end.temp, easing) + jitter(0.35)) * 10) / 10,
    humidity: Math.round(interpolate(start.humidity, end.humidity, easing) + jitter(2)),
    rain: Math.max(0, Math.round((interpolate(start.rain, end.rain, easing) + jitter(1.8)) * 10) / 10),
    waterLevel:
      Math.round((interpolate(start.waterLevel, end.waterLevel, easing) + jitter(2.4)) * 10) / 10,
    vibrationLevel:
      node.terrain === 'slope'
        ? index > total * 0.8
          ? Math.round(28 + random() * 18)
          : Math.round(random() * 10)
        : 0,
    aqi: Math.round(interpolate(start.aqi, end.aqi, easing) + jitter(7)),
    sos: false,
    battery: Math.round((interpolate(start.battery, end.battery, easing) + jitter(0.01)) * 100) / 100,
    rssi: Math.round(-62 - random() * 24),
    snr: Math.round((7 + random() * 4) * 10) / 10,
    packetId: `SEED-${node.id}-${String(index).padStart(3, '0')}`,
  };
}

function seedTelemetryHistory(store, nodes, random) {
  for (const node of nodes) {
    let previousWaterLevel = 40;
    const total = 37;

    for (let index = 0; index < total; index += 1) {
      const profile = { start: { temp: 28 + random()*2, humidity: 70 + random()*10, rain: 2 + random()*3, waterLevel: 35 + random()*10, aqi: 70 + random()*30, battery: 0.92 }, end: { temp: 31 + random()*3, humidity: 82 + random()*8, rain: 12 + random()*12, waterLevel: 82 + random()*28, aqi: 120 + random()*80, battery: 0.86 } };
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

export function seedSectorData(store, sectorCode = 'SECTOR-04') {
  const sector = getSector(sectorCode);
  const nodes = getSectorNodes(sectorCode);
  if (store.listNodes().length > 0) {
    // still allow site update
    store.setSite(sector);
    return false;
  }

  const random = seededRandom(20261026 + sectorCode.charCodeAt(sectorCode.length-1));
  store.transaction(() => {
    nodes.forEach((node) => store.insertNode(node));
    seedTelemetryHistory(store, nodes, random);
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
    store.setState('site', sector);
  });
  return true;
}

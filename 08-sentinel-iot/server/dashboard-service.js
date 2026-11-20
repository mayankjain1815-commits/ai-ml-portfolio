import config from './config.js';
import { SITE } from './site.js';
import { getSector } from './sectors.js';
import { RISK_LEVELS, batteryPercent, round } from './utils.js';
import { riskLevelToScore } from './risk-engine.js';

const ONLINE_WINDOW_MS = 6 * 60 * 1000;

function withEffectiveRisk(node, now) {
  const overrideActive =
    node.override &&
    (!node.override.until || new Date(node.override.until).getTime() > now);

  let risk = node.risk;
  if (overrideActive) {
    risk = {
      ...node.risk,
      score: riskLevelToScore(node.override.level),
      level: node.override.level,
      headline: `Manual ${node.override.level.toUpperCase()} risk override`,
      advisory: node.override.note,
      overridden: true,
      overrideBy: node.override.by,
      overrideUntil: node.override.until,
      sensorLevel: node.risk.level,
      sensorScore: node.risk.score,
    };
  }

  const lastSeenMs = node.lastSeen ? new Date(node.lastSeen).getTime() : 0;
  const online = Boolean(node.lastSeen) && now - lastSeenMs < ONLINE_WINDOW_MS;

  return {
    ...node,
    online,
    override: overrideActive ? node.override : null,
    risk,
    sensorRisk: node.risk,
    health: {
      online,
      batteryPercent: batteryPercent(node.latest.battery),
      batteryVoltage: node.latest.battery,
      rssi: node.latest.rssi,
      snr: node.latest.snr,
      packetCount: node.packetCount,
      lastSeen: node.lastSeen,
      ageSeconds: node.lastSeen ? Math.max(0, Math.round((now - lastSeenMs) / 1000)) : null,
      link:
        node.latest.rssi >= -95 ? 'nominal' : node.latest.rssi >= -110 ? 'degraded' : 'weak',
    },
  };
}

function buildSummary(nodes, alerts, evacuation) {
  const distribution = Object.fromEntries(RISK_LEVELS.map((level) => [level, 0]));
  let affectedPopulation = 0;
  let riskTotal = 0;

  for (const node of nodes) {
    distribution[node.risk.level] = (distribution[node.risk.level] ?? 0) + 1;
    riskTotal += node.risk.score;
    if (node.risk.level === 'high' || node.risk.level === 'severe') {
      affectedPopulation += node.population;
    }
  }

  const peakNode = nodes.reduce(
    (peak, node) => (!peak || node.risk.score > peak.risk.score ? node : peak),
    null,
  );
  const activeAlerts = alerts.filter((alert) => alert.status !== 'resolved');

  return {
    nodesTotal: nodes.length,
    nodesOnline: nodes.filter((node) => node.online).length,
    activeAlerts: activeAlerts.length,
    unacknowledgedAlerts: activeAlerts.filter((alert) => alert.status === 'active').length,
    criticalAlerts: activeAlerts.filter((alert) => alert.severity === 'severe').length,
    averageRisk: nodes.length ? round(riskTotal / nodes.length, 0) : 0,
    peakRisk: peakNode?.risk.score ?? 0,
    peakRiskLevel: peakNode?.risk.level ?? 'low',
    peakNode: peakNode ? { id: peakNode.id, name: peakNode.name } : null,
    affectedPopulation,
    riskDistribution: distribution,
    evacuationActive: Boolean(evacuation?.active),
    networkUptime: nodes.length
      ? round((nodes.filter((node) => node.online).length / nodes.length) * 100, 1)
      : 0,
  };
}

function buildWeather(nodes) {
  const online = nodes.filter((node) => node.online && node.latest.temp !== null);
  if (!online.length) {
    return { temp: null, humidity: null, rain: null, aqi: null };
  }
  const average = (key) => round(online.reduce((sum, node) => sum + Number(node.latest[key] ?? 0), 0) / online.length, 1);
  return {
    temp: average('temp'),
    humidity: average('humidity'),
    rain: average('rain'),
    aqi: Math.round(average('aqi')),
  };
}

export class DashboardService {
  constructor(store) {
    this.store = store;
  }

  getSnapshot() {
    const now = Date.now();
    const storedSite = this.store.getSite ? this.store.getSite(null) : null;
    const site = storedSite || SITE;
    const nodes = this.store.listNodes().map((node) => {
      const recent = this.store.getRecentTelemetry(node.id, 30).reverse();
      return {
        ...withEffectiveRisk(node, now),
        trends: {
          water: recent.map((reading) => reading.waterLevel),
          rain: recent.map((reading) => reading.rain),
          aqi: recent.map((reading) => reading.aqi),
          temp: recent.map((reading) => reading.temp),
          humidity: recent.map((reading) => reading.humidity),
        },
      };
    });
    const alerts = this.store.listAlerts({ includeResolved: false, limit: 30 });
    const incidents = this.store.listIncidents({ limit: 8 }).incidents;
    const evacuation = this.store.getState('evacuation', { active: false });
    const siren = this.store.getState('siren', { enabled: false });
    const gateways = this.store.getGateways().map((gateway) => ({
      ...gateway,
      online: Boolean(gateway.lastSeen) && now - new Date(gateway.lastSeen).getTime() < ONLINE_WINDOW_MS,
    }));

    return {
      meta: {
        application: 'SENTINEL',
        site,
        regionName: config.regionName,
        organization: 'District Disaster Management Authority',
        operator: config.operatorName,
        emergencyNumber: config.emergencyNumber,
        generatedAt: new Date(now).toISOString(),
        simulation: config.simulationEnabled,
        demoMode: config.simulationEnabled,
        version: config.version,
      },
      summary: buildSummary(nodes, alerts, evacuation),
      weather: buildWeather(nodes),
      nodes,
      alerts,
      incidents,
      incidentStats: this.store.getIncidentStats(),
      gateway: gateways[0] ?? {
        id: 'GW-NSK-01',
        online: false,
        packets: 0,
        lastSeen: null,
        rssi: null,
      },
      gateways,
      system: { evacuation, siren },
    };
  }

  getNodeHistory(nodeId, hours = 6) {
    const node = this.store.getNode(nodeId);
    if (!node) return null;
    return {
      node: withEffectiveRisk(node, Date.now()),
      history: this.store.getTelemetryHistory(nodeId, { hours, limit: 1000 }),
    };
  }
}

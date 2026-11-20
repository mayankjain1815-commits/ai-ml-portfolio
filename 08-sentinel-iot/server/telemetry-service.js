import { HAZARDS, assessRisk } from './risk-engine.js';
import { RISK_LEVEL_RANK } from './utils.js';

function metricsSummary(node, hazard) {
  const readable = {
    flood: `${node.latest.waterLevel.toFixed(0)} cm water depth · ${node.latest.rain.toFixed(1)} mm/h rain`,
    landslide: `${node.latest.rain.toFixed(1)} mm/h rain · ${Math.round(node.latest.vibrationLevel)}% vibration`,
    air_quality: `AQI ${Math.round(node.latest.aqi)} · ${node.latest.humidity.toFixed(0)}% humidity`,
    heat: `${node.latest.temp.toFixed(1)}°C · ${node.latest.humidity.toFixed(0)}% humidity`,
  };
  return readable[hazard] ?? '';
}

function alertTitle(type, nodeName) {
  return {
    flood: `Flood warning — ${nodeName}`,
    landslide: `Landslide warning — ${nodeName}`,
    air_quality: `Air quality alert — ${nodeName}`,
    heat: `Extreme heat warning — ${nodeName}`,
    sos: `Manual SOS — ${nodeName}`,
    evacuation: `EVACUATION ORDER — ${nodeName}`,
  }[type] ?? `Emergency alert — ${nodeName}`;
}

function previousHazardLevel(previousAssessment, hazardKey) {
  return previousAssessment?.hazards?.find((hazard) => hazard.key === hazardKey)?.level ?? 'low';
}

export class UnknownNodeError extends Error {
  constructor(nodeId) {
    super(`Sensor node ${nodeId} is not registered`);
    this.name = 'UnknownNodeError';
    this.nodeId = nodeId;
    this.status = 404;
  }
}

export class TelemetryService {
  constructor(store) {
    this.store = store;
  }

  ingest(reading, { gatewayId, source = 'gateway', firmware = null } = {}) {
    const node = this.store.getNode(reading.nodeId);
    if (!node) throw new UnknownNodeError(reading.nodeId);

    const resolvedGateway = gatewayId || node.gatewayId || 'GW-UNKNOWN';
    this.store.upsertGateway(resolvedGateway, {
      packets: 1,
      rssi: reading.rssi,
      firmware,
      status: 'online',
    });

    const recent = this.store.getRecentTelemetry(node.id, 8);
    const previousReading = recent[0] ?? null;
    const isStale =
      node.lastSeen && new Date(reading.timestamp).getTime() < new Date(node.lastSeen).getTime();

    this.store.insertTelemetry(node.id, reading);

    if (isStale) {
      return {
        accepted: true,
        ignored: true,
        reason: 'stale_timestamp',
        nodeId: node.id,
        timestamp: reading.timestamp,
        alerts: [],
        incidents: [],
      };
    }

    const previousAssessment = node.risk;
    const assessment = assessRisk(reading, {
      terrain: node.terrain,
      slopeRisk: node.slopeRisk,
      previousWaterLevel: previousReading?.waterLevel ?? reading.waterLevel,
    });
    this.store.updateNodeReading(node.id, reading, assessment);
    const updatedNode = this.store.getNode(node.id);

    const alerts = this.syncHazardAlerts(updatedNode, assessment, previousAssessment, source);
    const incidents = this.recordRiskTransition(updatedNode, previousAssessment, assessment);

    return {
      accepted: true,
      ignored: false,
      nodeId: updatedNode.id,
      timestamp: reading.timestamp,
      risk: assessment,
      alerts,
      incidents,
    };
  }

  ingestBatch(readings, { gatewayId, source = 'gateway', firmware = null } = {}) {
    const results = readings.map((reading) =>
      this.ingest(reading, { gatewayId, source, firmware }),
    );
    return {
      accepted: results.filter((result) => !result.ignored).length,
      ignored: results.filter((result) => result.ignored).length,
      results,
    };
  }

  syncHazardAlerts(node, assessment, previousAssessment, source) {
    const createdOrUpdated = [];

    for (const hazard of assessment.hazards) {
      if (!HAZARDS[hazard.key]) continue;
      const type = HAZARDS[hazard.key].alertType;
      const existing = this.store.getActiveAlertForNode(node.id, type);

      if (hazard.level === 'high' || hazard.level === 'severe') {
        const message = `${metricsSummary(node, type)}. ${
          hazard.factors
            .slice(0, 2)
            .map((factor) => `${factor.label} ${factor.value}`)
            .join('; ')
        }. ${HAZARDS[hazard.key].advisory}`;
        const metadata = {
          riskScore: assessment.score,
          hazardScore: hazard.score,
          factors: hazard.factors,
          capturedAt: assessment.evaluatedAt,
        };

        if (!existing) {
          const alert = this.store.createAlert({
            nodeId: node.id,
            nodeName: node.name,
            type,
            severity: hazard.level,
            title: alertTitle(type, node.name),
            message,
            status: 'active',
            source,
            metadata,
          });
          this.store.addIncident({
            nodeId: node.id,
            nodeName: node.name,
            type: 'alert',
            severity: hazard.level,
            title: alert.title,
            detail: message,
            source: 'automated',
            status: 'open',
            metadata: { alertId: alert.id },
          });
          createdOrUpdated.push(alert);
        } else if (RISK_LEVEL_RANK[hazard.level] > RISK_LEVEL_RANK[existing.severity]) {
          const alert = this.store.updateAlertEvidence(existing.id, {
            severity: hazard.level,
            message,
            metadata,
          });
          this.store.addIncident({
            nodeId: node.id,
            nodeName: node.name,
            type: 'alert',
            severity: hazard.level,
            title: `${HAZARDS[hazard.key].label} warning escalated`,
            detail: message,
            source: 'automated',
            status: 'open',
            metadata: { alertId: alert.id },
          });
          createdOrUpdated.push(alert);
        }
        continue;
      }

      // A warning is cleared only after two consecutive sub-threshold readings.
      // That hysteresis prevents a flapping sensor from opening and closing
      // emergency alerts every few seconds.
      const previousLevel = previousHazardLevel(previousAssessment, hazard.key);
      if (
        existing &&
        RISK_LEVEL_RANK[existing.severity] >= RISK_LEVEL_RANK.high &&
        RISK_LEVEL_RANK[previousLevel] < RISK_LEVEL_RANK.high &&
        RISK_LEVEL_RANK[hazard.level] < RISK_LEVEL_RANK.high
      ) {
        this.store.resolveAlert(existing.id);
        this.store.addIncident({
          nodeId: node.id,
          nodeName: node.name,
          type: 'alert',
          severity: 'moderate',
          title: `${HAZARDS[hazard.key].label} warning cleared`,
          detail: `Sensor readings returned below the high-risk threshold at ${node.name}.`,
          source: 'automated',
          status: 'resolved',
          metadata: { alertId: existing.id },
        });
      }
    }

    if (node.latest.sos) {
      const existingSos = this.store.getActiveAlertForNode(node.id, 'sos');
      if (!existingSos) {
        const alert = this.store.createAlert({
          nodeId: node.id,
          nodeName: node.name,
          type: 'sos',
          severity: 'severe',
          title: alertTitle('sos', node.name),
          message: `Tactile SOS button pressed at ${node.location}. GPS fix ${node.lat.toFixed(5)}, ${node.lon.toFixed(5)}. Respond immediately.`,
          status: 'active',
          source: 'hardware',
          metadata: { source: 'SW-420 manual button', battery: node.latest.battery },
        });
        this.store.addIncident({
          nodeId: node.id,
          nodeName: node.name,
          type: 'sos',
          severity: 'severe',
          title: `SOS received from ${node.name}`,
          detail: `Manual emergency button activated. Coordinates ${node.lat.toFixed(5)}, ${node.lon.toFixed(5)}.`,
          source: 'hardware',
          status: 'open',
          metadata: { alertId: alert.id },
        });
        createdOrUpdated.push(alert);
      }
    }

    return createdOrUpdated;
  }

  recordRiskTransition(node, previousAssessment, assessment) {
    const previousLevel = previousAssessment?.level ?? 'low';
    const previousRank = RISK_LEVEL_RANK[previousLevel] ?? 0;
    const nextRank = RISK_LEVEL_RANK[assessment.level] ?? 0;

    if (nextRank <= previousRank || nextRank < RISK_LEVEL_RANK.high) {
      return [];
    }

    const primaryHazard = assessment.hazards.find((hazard) => hazard.key === assessment.primaryHazard);
    const factorSummary = primaryHazard?.factors
      .slice(0, 2)
      .map((factor) => `${factor.label} ${factor.value}`)
      .join(', ');

    const incident = this.store.addIncident({
      nodeId: node.id,
      nodeName: node.name,
      type: 'sensor',
      severity: assessment.level,
      title: `${assessment.primaryHazardLabel} threshold crossed`,
      detail: `${factorSummary}. Composite risk index ${assessment.score}/100 at ${node.name}.`,
      source: 'sensor',
      status: 'monitoring',
      metadata: {
        riskScore: assessment.score,
        previousLevel,
        currentLevel: assessment.level,
        factors: primaryHazard?.factors,
      },
    });
    return [incident];
  }
}


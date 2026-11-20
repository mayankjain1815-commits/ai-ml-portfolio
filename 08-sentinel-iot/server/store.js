import fs from 'node:fs';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { createId, nowIso } from './utils.js';

function parseJson(value, fallback = null) {
  if (!value) return fallback;
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

function mapNode(row) {
  if (!row) return null;
  const overrideUntil = row.override_until;
  const overrideActive =
    Boolean(row.override_level) && (!overrideUntil || new Date(overrideUntil) > new Date());

  return {
    id: row.id,
    name: row.name,
    location: row.location,
    district: row.district,
    lat: row.lat,
    lon: row.lon,
    terrain: row.terrain,
    slopeRisk: row.slope_risk,
    population: row.population,
    gatewayId: row.gateway_id,
    installedAt: row.installed_at,
    lastSeen: row.last_seen,
    packetCount: row.packet_count,
    online: Boolean(row.online),
    latest: {
      temp: row.temp,
      humidity: row.humidity,
      rain: row.rain,
      waterLevel: row.water_level,
      vibration: Boolean(row.vibration),
      vibrationLevel: row.vibration_level,
      aqi: row.aqi,
      sos: Boolean(row.sos),
      battery: row.battery,
      rssi: row.rssi,
      snr: row.snr,
    },
    risk: parseJson(row.risk_json, {
      score: 0,
      level: 'low',
      primaryHazard: 'flood',
      hazards: [],
      topFactors: [],
    }),
    override:
      overrideActive && row.override_level
        ? {
            level: row.override_level,
            note: row.override_note,
            by: row.override_by,
            until: row.override_until,
          }
        : null,
  };
}

function mapAlert(row) {
  if (!row) return null;
  return {
    id: row.id,
    nodeId: row.node_id,
    nodeName: row.node_name,
    type: row.type,
    severity: row.severity,
    title: row.title,
    message: row.message,
    status: row.status,
    source: row.source,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    acknowledgedAt: row.acknowledged_at,
    acknowledgedBy: row.acknowledged_by,
    resolvedAt: row.resolved_at,
    metadata: parseJson(row.metadata_json, {}),
  };
}

function mapIncident(row) {
  if (!row) return null;
  return {
    id: row.id,
    nodeId: row.node_id,
    nodeName: row.node_name,
    type: row.type,
    severity: row.severity,
    title: row.title,
    detail: row.detail,
    source: row.source,
    status: row.status,
    createdAt: row.created_at,
    metadata: parseJson(row.metadata_json, {}),
  };
}

function mapTelemetry(row) {
  return {
    id: row.id,
    nodeId: row.node_id,
    timestamp: row.ts,
    lat: row.lat,
    lon: row.lon,
    temp: row.temp,
    humidity: row.humidity,
    rain: row.rain,
    waterLevel: row.water_level,
    vibration: Boolean(row.vibration),
    vibrationLevel: row.vibration_level,
    aqi: row.aqi,
    sos: Boolean(row.sos),
    battery: row.battery,
    rssi: row.rssi,
    snr: row.snr,
  };
}

export class SentinelStore {
  constructor(databasePath) {
    if (databasePath !== ':memory:') {
      fs.mkdirSync(path.dirname(databasePath), { recursive: true });
    }
    this.databasePath = databasePath;
    this.db = new DatabaseSync(databasePath);
    this.db.exec('PRAGMA journal_mode = WAL;');
    this.db.exec('PRAGMA foreign_keys = ON;');
    this.db.exec('PRAGMA busy_timeout = 5000;');
    this.migrate();
  }

  migrate() {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS nodes (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        location TEXT NOT NULL,
        district TEXT NOT NULL,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        terrain TEXT NOT NULL DEFAULT 'riverine',
        slope_risk REAL NOT NULL DEFAULT 50,
        population INTEGER NOT NULL DEFAULT 0,
        gateway_id TEXT,
        installed_at TEXT,
        last_seen TEXT,
        packet_count INTEGER NOT NULL DEFAULT 0,
        online INTEGER NOT NULL DEFAULT 1,
        temp REAL,
        humidity REAL,
        rain REAL,
        water_level REAL,
        vibration INTEGER NOT NULL DEFAULT 0,
        vibration_level REAL NOT NULL DEFAULT 0,
        aqi REAL,
        sos INTEGER NOT NULL DEFAULT 0,
        battery REAL,
        rssi REAL,
        snr REAL,
        risk_json TEXT,
        override_level TEXT,
        override_note TEXT,
        override_by TEXT,
        override_until TEXT
      );

      CREATE TABLE IF NOT EXISTS telemetry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        node_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
        ts TEXT NOT NULL,
        lat REAL,
        lon REAL,
        temp REAL,
        humidity REAL,
        rain REAL,
        water_level REAL,
        vibration INTEGER NOT NULL DEFAULT 0,
        vibration_level REAL NOT NULL DEFAULT 0,
        aqi REAL,
        sos INTEGER NOT NULL DEFAULT 0,
        battery REAL,
        rssi REAL,
        snr REAL,
        packet_id TEXT
      );

      CREATE INDEX IF NOT EXISTS telemetry_node_ts
        ON telemetry(node_id, ts DESC);

      CREATE TABLE IF NOT EXISTS alerts (
        id TEXT PRIMARY KEY,
        node_id TEXT,
        node_name TEXT,
        type TEXT NOT NULL,
        severity TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        source TEXT NOT NULL DEFAULT 'automated',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        acknowledged_at TEXT,
        acknowledged_by TEXT,
        resolved_at TEXT,
        metadata_json TEXT
      );

      CREATE INDEX IF NOT EXISTS alerts_status_created
        ON alerts(status, created_at DESC);

      CREATE TABLE IF NOT EXISTS incidents (
        id TEXT PRIMARY KEY,
        node_id TEXT,
        node_name TEXT,
        type TEXT NOT NULL,
        severity TEXT NOT NULL,
        title TEXT NOT NULL,
        detail TEXT NOT NULL,
        source TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        metadata_json TEXT
      );

      CREATE INDEX IF NOT EXISTS incidents_created
        ON incidents(created_at DESC);
      CREATE INDEX IF NOT EXISTS incidents_search
        ON incidents(severity, type, status);

      CREATE TABLE IF NOT EXISTS gateway_status (
        id TEXT PRIMARY KEY,
        last_seen TEXT,
        packets INTEGER NOT NULL DEFAULT 0,
        rssi REAL,
        status TEXT NOT NULL DEFAULT 'offline',
        firmware TEXT
      );

      CREATE TABLE IF NOT EXISTS system_state (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );
    `);
  }

  close() {
    this.db.close();
  }

  transaction(callback) {
    this.db.exec('BEGIN IMMEDIATE');
    try {
      const result = callback();
      this.db.exec('COMMIT');
      return result;
    } catch (error) {
      this.db.exec('ROLLBACK');
      throw error;
    }
  }

  insertNode(node) {
    this.db
      .prepare(
        `INSERT INTO nodes (
          id, name, location, district, lat, lon, terrain, slope_risk, population,
          gateway_id, installed_at, last_seen, online
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      )
      .run(
        node.id,
        node.name,
        node.location,
        node.district,
        node.lat,
        node.lon,
        node.terrain,
        node.slopeRisk,
        node.population,
        node.gatewayId,
        node.installedAt ?? nowIso(),
        null,
        node.online === false ? 0 : 1,
      );
    return this.getNode(node.id);
  }

  listNodes() {
    return this.db
      .prepare('SELECT * FROM nodes ORDER BY id ASC')
      .all()
      .map(mapNode);
  }

  getNode(id) {
    return mapNode(this.db.prepare('SELECT * FROM nodes WHERE id = ?').get(id));
  }

  updateNodeReading(nodeId, reading, assessment) {
    this.db
      .prepare(
        `UPDATE nodes SET
          lat = COALESCE(?, lat), lon = COALESCE(?, lon),
          temp = ?, humidity = ?, rain = ?, water_level = ?,
          vibration = ?, vibration_level = ?, aqi = ?, sos = ?,
          battery = ?, rssi = ?, snr = ?, last_seen = ?,
          packet_count = packet_count + 1, online = 1, risk_json = ?
        WHERE id = ?`,
      )
      .run(
        reading.lat ?? null,
        reading.lon ?? null,
        reading.temp,
        reading.humidity,
        reading.rain,
        reading.waterLevel,
        reading.vibrationLevel >= 20 ? 1 : 0,
        reading.vibrationLevel,
        reading.aqi,
        reading.sos ? 1 : 0,
        reading.battery,
        reading.rssi,
        reading.snr,
        reading.timestamp,
        JSON.stringify(assessment),
        nodeId,
      );
    return this.getNode(nodeId);
  }

  insertTelemetry(nodeId, reading) {
    const result = this.db
      .prepare(
        `INSERT INTO telemetry (
          node_id, ts, lat, lon, temp, humidity, rain, water_level, vibration,
          vibration_level, aqi, sos, battery, rssi, snr, packet_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      )
      .run(
        nodeId,
        reading.timestamp,
        reading.lat,
        reading.lon,
        reading.temp,
        reading.humidity,
        reading.rain,
        reading.waterLevel,
        reading.vibrationLevel >= 20 ? 1 : 0,
        reading.vibrationLevel,
        reading.aqi,
        reading.sos ? 1 : 0,
        reading.battery,
        reading.rssi,
        reading.snr,
        reading.packetId ?? null,
      );
    return Number(result.lastInsertRowid);
  }

  getRecentTelemetry(nodeId, limit = 20) {
    return this.db
      .prepare('SELECT * FROM telemetry WHERE node_id = ? ORDER BY ts DESC LIMIT ?')
      .all(nodeId, limit)
      .map(mapTelemetry);
  }

  getTelemetryHistory(nodeId, { hours = 6, limit = 500 } = {}) {
    const since = new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();
    return this.db
      .prepare(
        `SELECT * FROM telemetry
         WHERE node_id = ? AND ts >= ?
         ORDER BY ts ASC LIMIT ?`,
      )
      .all(nodeId, since, limit)
      .map(mapTelemetry);
  }

  createAlert(alert) {
    const timestamp = alert.createdAt ?? nowIso();
    const id = alert.id ?? createId('alt');
    this.db
      .prepare(
        `INSERT INTO alerts (
          id, node_id, node_name, type, severity, title, message, status,
          source, created_at, updated_at, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      )
      .run(
        id,
        alert.nodeId ?? null,
        alert.nodeName ?? null,
        alert.type,
        alert.severity,
        alert.title,
        alert.message,
        alert.status ?? 'active',
        alert.source ?? 'automated',
        timestamp,
        timestamp,
        JSON.stringify(alert.metadata ?? {}),
      );
    if (alert.status === 'acknowledged') {
      this.db
        .prepare(
          `UPDATE alerts
           SET acknowledged_at = ?, acknowledged_by = ?
           WHERE id = ?`,
        )
        .run(alert.acknowledgedAt ?? timestamp, alert.acknowledgedBy ?? 'Duty Officer', id);
    }
    if (alert.status === 'resolved') {
      this.db
        .prepare('UPDATE alerts SET resolved_at = ? WHERE id = ?')
        .run(alert.resolvedAt ?? timestamp, id);
    }
    return this.getAlert(id);
  }

  getAlert(id) {
    return mapAlert(this.db.prepare('SELECT * FROM alerts WHERE id = ?').get(id));
  }

  listAlerts({ status, nodeId, limit = 50, includeResolved = false } = {}) {
    const clauses = [];
    const params = {};
    if (status) {
      clauses.push('status = :status');
      params.status = status;
    } else if (!includeResolved) {
      clauses.push("status != 'resolved'");
    }
    if (nodeId) {
      clauses.push('node_id = :nodeId');
      params.nodeId = nodeId;
    }
    const where = clauses.length ? `WHERE ${clauses.join(' AND ')}` : '';
    return this.db
      .prepare(
        `SELECT * FROM alerts ${where}
         ORDER BY
           CASE severity WHEN 'severe' THEN 0 WHEN 'high' THEN 1 WHEN 'moderate' THEN 2 ELSE 3 END,
           created_at DESC
         LIMIT :limit`,
      )
      .all({ ...params, limit })
      .map(mapAlert);
  }

  getActiveAlertForNode(nodeId, type) {
    return mapAlert(
      this.db
        .prepare(
          `SELECT * FROM alerts
           WHERE node_id = ? AND type = ? AND status IN ('active', 'acknowledged')
           ORDER BY created_at DESC LIMIT 1`,
        )
        .get(nodeId, type),
    );
  }

  acknowledgeAlert(id, operator) {
    const timestamp = nowIso();
    const result = this.db
      .prepare(
        `UPDATE alerts
         SET status = 'acknowledged', acknowledged_at = ?, acknowledged_by = ?, updated_at = ?
         WHERE id = ? AND status = 'active'`,
      )
      .run(timestamp, operator, timestamp, id);
    if (result.changes === 0) return null;
    return this.getAlert(id);
  }

  updateAlertEvidence(id, { severity, message, metadata }) {
    this.db
      .prepare(
        `UPDATE alerts
         SET severity = ?, message = ?, metadata_json = ?, updated_at = ?
         WHERE id = ? AND status IN ('active', 'acknowledged')`,
      )
      .run(severity, message, JSON.stringify(metadata ?? {}), nowIso(), id);
    return this.getAlert(id);
  }

  acknowledgeAllAlerts(operator) {
    const timestamp = nowIso();
    const result = this.db
      .prepare(
        `UPDATE alerts
         SET status = 'acknowledged', acknowledged_at = ?, acknowledged_by = ?, updated_at = ?
         WHERE status = 'active'`,
      )
      .run(timestamp, operator, timestamp);
    return Number(result.changes);
  }

  resolveAlert(id) {
    const timestamp = nowIso();
    this.db
      .prepare("UPDATE alerts SET status = 'resolved', resolved_at = ?, updated_at = ? WHERE id = ?")
      .run(timestamp, timestamp, id);
    return this.getAlert(id);
  }

  resolveHazardAlerts(nodeId, type) {
    const timestamp = nowIso();
    const result = this.db
      .prepare(
        `UPDATE alerts
         SET status = 'resolved', resolved_at = ?, updated_at = ?
         WHERE node_id = ? AND type = ? AND status IN ('active', 'acknowledged')`,
      )
      .run(timestamp, timestamp, nodeId, type);
    return Number(result.changes);
  }

  resolveAlertsByType(type) {
    const timestamp = nowIso();
    const result = this.db
      .prepare(
        `UPDATE alerts
         SET status = 'resolved', resolved_at = ?, updated_at = ?
         WHERE type = ? AND status IN ('active', 'acknowledged')`,
      )
      .run(timestamp, timestamp, type);
    return Number(result.changes);
  }

  addIncident(incident) {
    const id = incident.id ?? createId('inc');
    this.db
      .prepare(
        `INSERT INTO incidents (
          id, node_id, node_name, type, severity, title, detail,
          source, status, created_at, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      )
      .run(
        id,
        incident.nodeId ?? null,
        incident.nodeName ?? null,
        incident.type,
        incident.severity,
        incident.title,
        incident.detail,
        incident.source,
        incident.status ?? 'open',
        incident.createdAt ?? nowIso(),
        JSON.stringify(incident.metadata ?? {}),
      );
    return mapIncident(this.db.prepare('SELECT * FROM incidents WHERE id = ?').get(id));
  }

  listIncidents(filters = {}) {
    const {
      search = '',
      severity,
      type,
      status,
      source,
      from,
      to,
      limit = 50,
      offset = 0,
    } = filters;
    const clauses = [];
    const params = {};

    if (search) {
      clauses.push('(title LIKE :search OR detail LIKE :search OR node_name LIKE :search)');
      params.search = `%${search}%`;
    }
    if (severity) {
      clauses.push('severity = :severity');
      params.severity = severity;
    }
    if (type) {
      clauses.push('type = :type');
      params.type = type;
    }
    if (status) {
      clauses.push('status = :status');
      params.status = status;
    }
    if (source) {
      clauses.push('source = :source');
      params.source = source;
    }
    if (from) {
      clauses.push('created_at >= :from');
      params.from = from;
    }
    if (to) {
      clauses.push('created_at <= :to');
      params.to = to;
    }

    const where = clauses.length ? `WHERE ${clauses.join(' AND ')}` : '';
    const rows = this.db
      .prepare(
        `SELECT * FROM incidents ${where}
         ORDER BY created_at DESC LIMIT :limit OFFSET :offset`,
      )
      .all({ ...params, limit: Math.min(Number(limit) || 50, 5000), offset: Number(offset) || 0 });
    const total = this.db
      .prepare(`SELECT COUNT(*) AS total FROM incidents ${where}`)
      .get(params).total;

    return { incidents: rows.map(mapIncident), total, limit, offset };
  }

  getIncidentStats() {
    return this.db
      .prepare(
        `SELECT severity, COUNT(*) AS count
         FROM incidents
         WHERE created_at >= ?
         GROUP BY severity`,
      )
      .all(new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString())
      .reduce((acc, row) => ({ ...acc, [row.severity]: row.count }), {
        low: 0,
        moderate: 0,
        high: 0,
        severe: 0,
      });
  }

  upsertGateway(id, { packets = 1, rssi = null, firmware = null, status = 'online' } = {}) {
    const timestamp = nowIso();
    this.db
      .prepare(
        `INSERT INTO gateway_status (id, last_seen, packets, rssi, status, firmware)
         VALUES (?, ?, ?, ?, ?, ?)
         ON CONFLICT(id) DO UPDATE SET
           last_seen = excluded.last_seen,
           packets = packets + excluded.packets,
           rssi = excluded.rssi,
           status = excluded.status,
           firmware = COALESCE(excluded.firmware, gateway_status.firmware)`,
      )
      .run(id, timestamp, packets, rssi, status, firmware);
    return this.getGateway(id);
  }

  getGateway(id) {
    const row = this.db.prepare('SELECT * FROM gateway_status WHERE id = ?').get(id);
    if (!row) return null;
    return {
      id: row.id,
      lastSeen: row.last_seen,
      packets: row.packets,
      rssi: row.rssi,
      status: row.status,
      firmware: row.firmware,
    };
  }

  getGateways() {
    return this.db
      .prepare('SELECT * FROM gateway_status ORDER BY last_seen DESC')
      .all()
      .map((row) => ({
        id: row.id,
        lastSeen: row.last_seen,
        packets: row.packets,
        rssi: row.rssi,
        status: row.status,
        firmware: row.firmware,
      }));
  }

  setOverride(nodeId, override) {
    this.db
      .prepare(
        `UPDATE nodes
         SET override_level = ?, override_note = ?, override_by = ?, override_until = ?
         WHERE id = ?`,
      )
      .run(override.level, override.note, override.by, override.until, nodeId);
    return this.getNode(nodeId);
  }

  clearOverride(nodeId) {
    this.db
      .prepare(
        `UPDATE nodes
         SET override_level = NULL, override_note = NULL, override_by = NULL, override_until = NULL
         WHERE id = ?`,
      )
      .run(nodeId);
    return this.getNode(nodeId);
  }

  getState(key, fallback = null) {
    const row = this.db.prepare('SELECT value FROM system_state WHERE key = ?').get(key);
    if (!row) return fallback;
    return parseJson(row.value, fallback);
  }

  setState(key, value) {
    this.db
      .prepare(
        `INSERT INTO system_state (key, value, updated_at)
         VALUES (?, ?, ?)
         ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at`,
      )
      .run(key, JSON.stringify(value), nowIso());
    return value;
  }

  pruneOldData(retentionDays = 30) {
    const cutoff = new Date(Date.now() - retentionDays * 24 * 60 * 60 * 1000).toISOString();
    this.db.prepare('DELETE FROM telemetry WHERE ts < ?').run(cutoff);
    this.db
      .prepare("DELETE FROM incidents WHERE created_at < ? AND status = 'resolved'")
      .run(cutoff);
    this.db
      .prepare("DELETE FROM alerts WHERE created_at < ? AND status = 'resolved'")
      .run(cutoff);
  }

  setSite(site) {
    this.setState('site', site);
  }

  getSite(fallback) {
    return this.getState('site', fallback);
  }
}

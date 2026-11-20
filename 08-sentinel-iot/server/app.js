import fs from 'node:fs';
import express from 'express';
import compression from 'compression';
import { ZodError } from 'zod';
import config from './config.js';
import { SITE } from './site.js';
import { DashboardService } from './dashboard-service.js';
import { CommandService } from './command-service.js';
import { TelemetryService } from './telemetry-service.js';
import { commandSchemas, gatewayBatchSchema, telemetrySchema } from './validation.js';
import { createId } from './utils.js';
import { helmetConfig, corsOptions, apiLimiter } from './middleware/security.js';
import authRoutes from './routes/auth.js';
import alertsExtendedRoutes from './routes/alerts-extended.js';
import evacuationRoutes from './routes/evacuation.js';
import multiAuthRoutes from './routes/multi-auth.js';
import cors from 'cors';
import { authenticateToken, requireRole } from './middleware/auth.js';

function csvEscape(value) {
  const text = String(value ?? '');
  return `"${text.replaceAll('"', '""')}"`;
}

function parseOperator(request) {
  return request.get('x-operator-name') || request.body?.operator;
}

function requireGatewayKey(req, res, next) {
  const token = req.get('x-gateway-key') || req.get('authorization')?.replace(/^Bearer\s+/i, '');
  if (token !== config.gatewayKey) {
    res.status(401).json({ ok: false, error: 'Invalid gateway key' });
    return;
  }
  next();
}

function parseInteger(value, fallback, minimum, maximum) {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(maximum, Math.max(minimum, parsed));
}

function paginationParams(query) {
  return {
    limit: parseInteger(query.limit, 40, 1, 200),
    offset: parseInteger(query.offset, 0, 0, 1_000_000),
  };
}

export function createApp({
  store,
  broadcast = () => {},
  simulate = config.simulationEnabled,
  simulationStatus = () => ({}),
} = {}) {
  if (!store) throw new Error('createApp requires a SentinelStore instance');

  const telemetryService = new TelemetryService(store);
  const commandService = new CommandService(store);
  const dashboardService = new DashboardService(store);
  const app = express();

  app.disable('x-powered-by');
  app.use(helmetConfig);
  app.use(cors(corsOptions));
  app.use(compression());
  app.use(express.json({ limit: '64kb' }));
  app.use(express.urlencoded({ extended: true, limit: '64kb' }));
  app.use(apiLimiter);

  app.use((req, res, next) => {
    req.requestId = createId('req');
    res.setHeader('X-Request-Id', req.requestId);
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('X-Frame-Options', 'DENY');
    res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
    res.setHeader('Permissions-Policy', 'geolocation=(), microphone=(), camera=()');
    next();
  });

  app.use('/api/auth', authRoutes);
  app.use('/api/multi-auth', multiAuthRoutes);
  app.use('/api/evacuation', evacuationRoutes);
  app.use('/api', alertsExtendedRoutes);

  app.get('/api/health', (req, res) => {
    const snapshot = dashboardService.getSnapshot();
    res.json({
      ok: true,
      service: 'sentinel-iot-command',
      version: config.version,
      environment: config.nodeEnv,
      uptimeSeconds: Math.round(process.uptime()),
      simulation: simulate,
      database: store.databasePath === ':memory:' ? 'memory' : 'sqlite',
      nodes: { total: snapshot.summary.nodesTotal, online: snapshot.summary.nodesOnline },
      timestamp: new Date().toISOString(),
    });
  });

  app.get('/api/meta', (req, res) => {
    res.json({ ...dashboardService.getSnapshot().meta, simulationStatus: simulationStatus() });
  });

  app.get('/api/dashboard', (req, res) => {
    res.json({ ok: true, data: dashboardService.getSnapshot() });
  });

  app.get('/api/nodes', (req, res) => {
    res.json({ ok: true, data: dashboardService.getSnapshot().nodes });
  });

  app.get('/api/nodes/:nodeId', (req, res) => {
    const node = store.getNode(req.params.nodeId);
    if (!node) return res.status(404).json({ ok: false, error: 'Sensor node not found' });
    return res.json({ ok: true, data: dashboardService.getNodeHistory(req.params.nodeId, 6) });
  });

  app.get('/api/nodes/:nodeId/history', (req, res) => {
    const hours = parseInteger(req.query.hours, 6, 1, 168);
    const data = dashboardService.getNodeHistory(req.params.nodeId, hours);
    if (!data) return res.status(404).json({ ok: false, error: 'Sensor node not found' });
    return res.json({ ok: true, data });
  });

  app.get('/api/alerts', (req, res) => {
    const status = ['active', 'acknowledged', 'resolved'].includes(req.query.status) ? req.query.status : undefined;
    const includeResolved = req.query.status === 'all';
    const alerts = store.listAlerts({ status, includeResolved, limit: parseInteger(req.query.limit, 60, 1, 200) });
    res.json({ ok: true, data: alerts });
  });

  app.get('/api/incidents', (req, res) => {
    const { limit, offset } = paginationParams(req.query);
    const result = store.listIncidents({
      search: String(req.query.search ?? '').slice(0, 120),
      severity: req.query.severity,
      type: req.query.type,
      status: req.query.status,
      source: req.query.source,
      from: req.query.from,
      to: req.query.to,
      limit,
      offset,
    });
    res.json({ ok: true, ...result });
  });

  app.get('/api/incidents/stats', (req, res) => {
    res.json({ ok: true, data: store.getIncidentStats() });
  });

  app.get('/api/incidents/export.csv', (req, res) => {
    const result = store.listIncidents({
      search: String(req.query.search ?? '').slice(0, 120),
      severity: req.query.severity,
      type: req.query.type,
      status: req.query.status,
      source: req.query.source,
      from: req.query.from,
      to: req.query.to,
      limit: 5000,
      offset: 0,
    });
    const header = ['Timestamp', 'Event ID', 'Node', 'Type', 'Severity', 'Title', 'Detail', 'Source', 'Status'];
    const rows = result.incidents.map((incident) =>
      [incident.createdAt, incident.id, incident.nodeName ?? '', incident.type, incident.severity, incident.title, incident.detail, incident.source, incident.status]
        .map(csvEscape)
        .join(','),
    );
    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', 'attachment; filename="sentinel-incidents.csv"');
    res.send([header.join(','), ...rows].join('\n'));
  });

  app.post('/api/v1/telemetry', requireGatewayKey, (req, res) => {
    let response;
    if (Array.isArray(req.body?.readings)) {
      const payload = gatewayBatchSchema.parse(req.body);
      const result = telemetryService.ingestBatch(payload.readings, {
        gatewayId: payload.gatewayId,
        source: 'gateway-http',
        firmware: payload.firmware,
      });
      response = {
        accepted: result.accepted,
        ignored: result.ignored,
        nodes: result.results.map((item) => ({ nodeId: item.nodeId, ignored: item.ignored, riskLevel: item.risk?.level ?? null })),
      };
    } else {
      const reading = telemetrySchema.parse(req.body);
      const result = telemetryService.ingest(reading, { gatewayId: req.get('x-gateway-id') || undefined, source: 'gateway-http' });
      response = { accepted: result.ignored ? 0 : 1, ignored: result.ignored ? 1 : 0, nodes: [{ nodeId: result.nodeId, ignored: result.ignored, riskLevel: result.risk?.level ?? null }] };
    }
    broadcast();
    res.status(202).json({ ok: true, ...response, evaluatedAt: new Date().toISOString() });
  });

  app.post('/api/alerts/acknowledge-all', (req, res) => {
    const { operator } = commandSchemas.acknowledge.parse(req.body ?? {});
    const count = commandService.acknowledgeAll(parseOperator(req) || operator);
    broadcast();
    res.json({ ok: true, acknowledged: count });
  });

  app.post('/api/alerts/:alertId/acknowledge', authenticateToken, requireRole(['admin', 'operator']), (req, res) => {
    const { operator } = commandSchemas.acknowledge.parse(req.body ?? {});
    const alert = commandService.acknowledgeAlert(req.params.alertId, parseOperator(req) || req.user?.username || operator);
    broadcast();
    res.json({ ok: true, data: alert });
  });

  app.post('/api/alerts/acknowledge-all', authenticateToken, requireRole(['admin', 'operator']), (req, res) => {
    const { operator } = commandSchemas.acknowledge.parse(req.body ?? {});
    const count = commandService.acknowledgeAll(parseOperator(req) || req.user?.username || operator);
    broadcast();
    res.json({ ok: true, data: { acknowledged: count } });
  });

  app.post('/api/commands/evacuation', authenticateToken, requireRole(['admin', 'operator']), (req, res) => {
    const payload = commandSchemas.evacuation.parse(req.body ?? {});
    const result = commandService.issueEvacuation({ nodeId: payload.nodeId, reason: payload.reason, operator: parseOperator(req) || req.user?.username || payload.operator });
    broadcast();
    res.status(201).json({ ok: true, data: result });
  });

  app.post('/api/commands/all-clear', authenticateToken, requireRole(['admin', 'operator']), (req, res) => {
    const result = commandService.clearEvacuation(parseOperator(req) || req.user?.username);
    broadcast();
    res.json({ ok: true, data: result });
  });

  app.post('/api/commands/override', authenticateToken, requireRole(['admin']), (req, res) => {
    const payload = commandSchemas.override.parse(req.body ?? {});
    const result = commandService.overrideRisk({ ...payload, operator: parseOperator(req) || req.user?.username || payload.operator });
    broadcast();
    res.json({ ok: true, data: result });
  });

  app.delete('/api/nodes/:nodeId/override', authenticateToken, requireRole(['admin']), (req, res) => {
    const result = commandService.clearOverride(req.params.nodeId, parseOperator(req) || req.user?.username);
    broadcast();
    res.json({ ok: true, data: result });
  });

  app.post('/api/commands/test-sos', authenticateToken, requireRole(['admin', 'operator']), (req, res) => {
    const payload = commandSchemas.sosTest.parse(req.body ?? {});
    const result = commandService.triggerSos(payload.nodeId, parseOperator(req) || req.user?.username || payload.operator);
    broadcast();
    res.status(201).json({ ok: true, data: result });
  });

  app.post('/api/commands/siren', authenticateToken, requireRole(['admin', 'operator']), (req, res) => {
    const payload = commandSchemas.siren.parse(req.body ?? {});
    const state = commandService.setSiren(payload.enabled, parseOperator(req) || req.user?.username || payload.operator);
    broadcast();
    res.json({ ok: true, data: state });
  });

  app.post('/api/site/switch', authenticateToken, requireRole(['admin']), async (req, res) => {
    const { code } = req.body || {};
    if (!code) {
      return res.status(400).json({ ok: false, error: 'Sector code required' });
    }
    try {
      const { SectorManager } = await import('./sector-manager.js');
      const manager = new SectorManager(store);
      const result = manager.switchSector(code);
      broadcast();
      res.json({ ok: true, data: result.sector, nodes: result.nodes.length });
    } catch (err) {
      res.status(400).json({ ok: false, error: err.message });
    }
  });

  app.get('/api/site', (req, res) => {
    const stored = store.getSite ? store.getSite(null) : null;
    res.json({ ok: true, data: stored || SITE });
  });

  app.use('/api', (req, res) => {
    res.status(404).json({ ok: false, error: `Unknown API route: ${req.method} ${req.originalUrl}` });
  });

  if (fs.existsSync(config.distPath)) {
    app.use(express.static(config.distPath, { index: false, maxAge: config.isProduction ? '1h' : 0 }));
    app.get(/^(?!\/api|\/ws).*/, (req, res) => {
      res.sendFile('index.html', { root: config.distPath });
    });
  } else {
    app.get('/', (req, res) => {
      res.json({ ok: true, message: 'SENTINEL API is running. Start the UI with `npm run dev` or build it with `npm run build`.', dashboard: '/api/dashboard' });
    });
  }

  app.use((error, req, res, next) => {
    if (res.headersSent) return next(error);
    if (error instanceof ZodError) {
      return res.status(400).json({ ok: false, error: 'Invalid payload', issues: error.issues.map((issue) => ({ path: issue.path.join('.'), message: issue.message })) });
    }
    if (error.status && error.status < 500) {
      return res.status(error.status).json({ ok: false, error: error.message });
    }
    if (config.nodeEnv !== 'production') {
      console.error(`[api] ${req.method} ${req.originalUrl}`, error);
    }
    return res.status(500).json({ ok: false, error: 'Internal server error' });
  });

  app.locals.services = { telemetryService, commandService, dashboardService };
  return app;
}

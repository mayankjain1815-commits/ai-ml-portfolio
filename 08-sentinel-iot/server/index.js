import http from 'node:http';
import config from './config.js';
import { SentinelStore } from './store.js';
import { seedDemoData } from './seed.js';
import { seedSectorData } from './seed-sector.js';
import { createApp } from './app.js';
import { RealtimeHub } from './realtime.js';
import { SimulationEngine } from './simulator.js';

const store = new SentinelStore(config.databasePath);
let seeded = seedDemoData(store);
if (!seeded && store.listNodes().length === 0) {
  seeded = seedSectorData(store, 'SECTOR-04');
} else if (store.listNodes().length > 0) {
  const existingSite = store.getSite ? store.getSite(null) : null;
  if (!existingSite) {
    const { SITE } = await import('./site.js');
    store.setSite(SITE);
  }
}

let realtimeHub = null;
let simulator = null;
let shuttingDown = false;

const broadcast = () => {
  realtimeHub?.broadcastSnapshot();
};

const app = createApp({
  store,
  broadcast,
  simulate: config.simulationEnabled,
  simulationStatus: () =>
    simulator
      ? {
          running: simulator.running,
          intervalMs: simulator.intervalMs,
          lastError: simulator.lastError,
        }
      : { running: false },
});

const server = http.createServer(app);
const dashboardService = app.locals.services.dashboardService;

realtimeHub = new RealtimeHub({
  server,
  store,
  telemetryService: app.locals.services.telemetryService,
  getSnapshot: () => dashboardService.getSnapshot(),
  gatewayKey: config.gatewayKey,
});

if (config.simulationEnabled) {
  simulator = new SimulationEngine({
    store,
    telemetryService: app.locals.services.telemetryService,
    intervalMs: config.simulationIntervalMs,
    onTick: broadcast,
  });
}

store.pruneOldData(config.retentionDays);
const retentionTimer = setInterval(() => store.pruneOldData(config.retentionDays), 6 * 60 * 60 * 1000);
retentionTimer.unref();

server.listen(config.port, () => {
  const protocol = config.isProduction ? 'https' : 'http';
  console.log(`[sentinel] ${seeded ? 'seeded demo network' : 'loaded existing telemetry'} · ${config.databasePath}`);
  console.log(`[sentinel] dashboard ${protocol}://localhost:${config.port}`);
  console.log(`[sentinel] websocket ws://localhost:${config.port}/ws`);
  console.log(
    `[sentinel] simulation ${config.simulationEnabled ? `ON every ${config.simulationIntervalMs}ms` : 'OFF'} · env ${config.nodeEnv}`,
  );
  if (config.simulationEnabled) {
    simulator.start();
  }
});

server.on('error', (error) => {
  console.error('[sentinel] server error:', error.message);
  process.exitCode = 1;
});

function shutdown(signal) {
  if (shuttingDown) return;
  shuttingDown = true;
  console.log(`[sentinel] ${signal} received — shutting down`);
  clearInterval(retentionTimer);
  simulator?.stop();
  realtimeHub?.close();
  server.close(() => {
    store.close();
    process.exit(0);
  });
  setTimeout(() => process.exit(1), 5000).unref();
}

process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('unhandledRejection', (error) => {
  console.error('[sentinel] unhandled rejection:', error);
});

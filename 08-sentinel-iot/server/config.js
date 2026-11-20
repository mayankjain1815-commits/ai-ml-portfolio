import path from 'node:path';
import { fileURLToPath } from 'node:url';
import dotenv from 'dotenv';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
dotenv.config({ path: path.join(projectRoot, '.env'), quiet: true });

const asBoolean = (value, fallback) => {
  if (value === undefined) return fallback;
  return ['1', 'true', 'yes', 'on'].includes(String(value).toLowerCase());
};

const asInteger = (value, fallback) => {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : fallback;
};

export const config = {
  projectRoot,
  nodeEnv: process.env.NODE_ENV ?? 'development',
  port: asInteger(process.env.PORT, 5108),
  databasePath: process.env.DATABASE_PATH ?? path.join(projectRoot, 'data', 'sentinel.db'),
  gatewayKey: process.env.GATEWAY_KEY ?? 'gw-sentinel-demo-key',
  jwtSecret: process.env.JWT_SECRET || 'change-me-in-production',
  sessionSecret: process.env.SESSION_SECRET || 'change-me-session',
  corsOrigin: process.env.CORS_ORIGIN || (process.env.NODE_ENV === 'production' ? '' : '*'),
  adminUsername: process.env.ADMIN_USERNAME || 'admin',
  adminPassword: process.env.ADMIN_PASSWORD || 'admin',
  operatorUsername: process.env.OPERATOR_USERNAME || 'operator',
  operatorPassword: process.env.OPERATOR_PASSWORD || 'operator',
  simulationEnabled: asBoolean(process.env.SIMULATION, false),
  simulationIntervalMs: Math.max(2000, asInteger(process.env.SIMULATION_INTERVAL_MS, 4000)),
  operatorName: process.env.OPERATOR_NAME ?? 'Duty Officer M. Rao',
  regionName: process.env.REGION_NAME ?? 'Nashik Basin',
  emergencyNumber: process.env.EMERGENCY_NUMBER ?? '112',
  version: '1.0.0',
  isProduction: process.env.NODE_ENV === 'production',
  retentionDays: Math.max(1, asInteger(process.env.RETENTION_DAYS, 30)),
  distPath: path.join(projectRoot, 'dist'),
  maxTelemetryBatch: 24,
};

export default config;

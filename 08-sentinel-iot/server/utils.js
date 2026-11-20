import { randomUUID } from 'node:crypto';

export const RISK_LEVELS = ['low', 'moderate', 'high', 'severe'];

export const RISK_LEVEL_RANK = {
  low: 0,
  moderate: 1,
  high: 2,
  severe: 3,
};

export function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, Number(value) || 0));
}

export function round(value, decimals = 1) {
  const factor = 10 ** decimals;
  return Math.round((Number(value) + Number.EPSILON) * factor) / factor;
}

export function riskLevelFromScore(score) {
  if (score >= 75) return 'severe';
  if (score >= 50) return 'high';
  if (score >= 25) return 'moderate';
  return 'low';
}

export function levelIsAtLeast(level, threshold) {
  return (RISK_LEVEL_RANK[level] ?? 0) >= (RISK_LEVEL_RANK[threshold] ?? 0);
}

export function formatLevel(level) {
  return String(level ?? 'low').toUpperCase();
}

export function createId(prefix = 'evt') {
  return `${prefix}_${randomUUID().replaceAll('-', '').slice(0, 16)}`;
}

export function nowIso() {
  return new Date().toISOString();
}

export function seededRandom(seed = 42) {
  let state = seed >>> 0;
  return () => {
    state += 0x6d2b79f5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

export function toIsoDate(value, fallback = nowIso()) {
  if (!value) return fallback;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? fallback : parsed.toISOString();
}

export function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

export function normalizeVibration(vibration) {
  if (typeof vibration === 'boolean') {
    return vibration ? 100 : 0;
  }

  const level = clamp(vibration, 0, 100);
  return level;
}

export function batteryPercent(voltage) {
  // A single 18650 cell: 3.30 V empty, 4.20 V full, with a small non-linear tail.
  const normalized = clamp((Number(voltage) - 3.3) / 0.9, 0, 1);
  return Math.round((0.08 + normalized * 0.92) * 100);
}

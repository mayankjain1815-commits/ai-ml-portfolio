const LOCALE = 'en-IN';
const TIME_ZONE = 'Asia/Kolkata';

const timeFormatter = new Intl.DateTimeFormat(LOCALE, {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
  timeZone: TIME_ZONE,
});

const shortTimeFormatter = new Intl.DateTimeFormat(LOCALE, {
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
  timeZone: TIME_ZONE,
});

const dateFormatter = new Intl.DateTimeFormat(LOCALE, {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  timeZone: TIME_ZONE,
});

const dateTimeFormatter = new Intl.DateTimeFormat(LOCALE, {
  day: '2-digit',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
  timeZone: TIME_ZONE,
});

export const RISK_ORDER = ['low', 'moderate', 'high', 'severe'];

export const RISK_LABELS = {
  low: 'Low',
  moderate: 'Moderate',
  high: 'High',
  severe: 'Severe',
};

export const ALERT_TYPE_LABELS = {
  flood: 'Flood',
  landslide: 'Landslide',
  air_quality: 'Air quality',
  heat: 'Extreme heat',
  sos: 'Manual SOS',
  evacuation: 'Evacuation',
};

export const INCIDENT_TYPE_LABELS = {
  alert: 'Warning',
  sensor: 'Sensor event',
  sos: 'Manual SOS',
  command: 'Command',
  acknowledgement: 'Acknowledgment',
  gateway: 'Gateway',
  evacuation: 'Evacuation',
  drill: 'Drill',
};

export const SOURCE_LABELS = {
  automated: 'Risk engine',
  sensor: 'Sensor node',
  operator: 'Operator',
  system: 'System',
  hardware: 'Hardware',
  simulator: 'Simulator',
  'gateway-http': 'Gateway HTTP',
  'gateway-ws': 'Gateway WS',
};

export function formatClock(value = new Date()) {
  return timeFormatter.format(new Date(value));
}

export function formatTime(value) {
  if (!value) return '—';
  return shortTimeFormatter.format(new Date(value));
}

export function formatDate(value) {
  if (!value) return '—';
  return dateFormatter.format(new Date(value));
}

export function formatDateTime(value) {
  if (!value) return '—';
  return dateTimeFormatter.format(new Date(value));
}

export function formatRelative(value) {
  if (!value) return '—';
  const milliseconds = Date.now() - new Date(value).getTime();
  const seconds = Math.max(0, Math.round(milliseconds / 1000));
  if (seconds < 10) return 'just now';
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function formatAge(seconds) {
  if (seconds === null || seconds === undefined) return 'No packet';
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m ago`;
}

export function formatNumber(value, options = {}) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 1,
    ...options,
  }).format(Number(value));
}

export function formatCoordinate(value, axis) {
  if (value === null || value === undefined) return '—';
  const direction = axis === 'lat' ? (value >= 0 ? 'N' : 'S') : value >= 0 ? 'E' : 'W';
  return `${Math.abs(value).toFixed(5)}° ${direction}`;
}

export function riskLabel(level) {
  return RISK_LABELS[level] ?? 'Low';
}

export function riskShort(level) {
  return (RISK_LABELS[level] ?? 'Low').toUpperCase();
}

export function alertTypeLabel(type) {
  return ALERT_TYPE_LABELS[type] ?? type?.replaceAll('_', ' ') ?? 'Alert';
}

export function incidentTypeLabel(type) {
  return INCIDENT_TYPE_LABELS[type] ?? type?.replaceAll('_', ' ') ?? 'Event';
}

export function sourceLabel(source) {
  return SOURCE_LABELS[source] ?? source?.replaceAll('_', ' ') ?? 'Unknown';
}

export function titleCase(value) {
  if (!value) return '';
  return String(value).replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function formatBattery(voltage) {
  if (voltage === null || voltage === undefined) return '—';
  return `${Number(voltage).toFixed(2)} V`;
}

export function batteryTone(percent) {
  if (percent === null || percent === undefined) return 'unknown';
  if (percent < 30) return 'critical';
  if (percent < 60) return 'watch';
  return 'nominal';
}

export function humanFileTimestamp(value = new Date()) {
  return new Date(value).toISOString().replaceAll(':', '-').slice(0, 19);
}

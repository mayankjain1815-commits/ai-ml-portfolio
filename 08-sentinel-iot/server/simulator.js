import { clamp } from './utils.js';

function smooth(previous, target, rate) {
  return previous + (target - previous) * rate;
}

function jitter(amplitude) {
  return (Math.random() - 0.5) * 2 * amplitude;
}

function round(value, decimals = 1) {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}

/**
 * Produces correlated, slowly moving telemetry rather than independent random
 * values. The UI can therefore demonstrate a developing emergency (rising water,
 * intermittent slope vibration) instead of a slot machine of numbers.
 */
export class SimulationEngine {
  constructor({ store, telemetryService, intervalMs, onTick }) {
    this.store = store;
    this.telemetryService = telemetryService;
    this.intervalMs = intervalMs;
    this.onTick = onTick;
    this.timer = null;
    this.running = false;
    this.packetCounter = 0;
    this.lastError = null;
  }

  start() {
    if (this.running) return;
    this.running = true;
    this.tick();
    this.timer = setInterval(() => this.tick(), this.intervalMs);
    this.timer.unref();
  }

  stop() {
    this.running = false;
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
  }

  buildReading(node) {
    const latest = node.latest;
    const elapsed = Date.now() / 1000;
    const common = {
      nodeId: node.id,
      timestamp: new Date().toISOString(),
      lat: round(node.lat + jitter(0.000025), 6),
      lon: round(node.lon + jitter(0.000025), 6),
      sos: false,
      rssi: Math.round(-66 - Math.random() * 24),
      snr: round(6 + Math.random() * 6, 1),
      packetId: `SIM-${node.id}-${Date.now()}-${this.packetCounter}`,
    };

    let reading;
    if (node.id === 'SN-NASH-01') {
      const rainTarget = 25 + 5 * Math.sin(elapsed / 58 + 0.5);
      const rain = clamp(smooth(latest.rain, rainTarget, 0.14) + jitter(0.5), 0, 60);
      reading = {
        temp: round(smooth(latest.temp, 28.4 + 0.5 * Math.sin(elapsed / 120), 0.05) + jitter(0.08), 1),
        humidity: round(clamp(smooth(latest.humidity, 93.5, 0.05) + jitter(0.4), 0, 100), 1),
        rain: round(rain, 1),
        waterLevel: round(clamp(latest.waterLevel + (rain - 17) * 0.014 + jitter(0.12), 80, 148), 1),
        vibrationLevel: Math.round(Math.random() * 6),
        aqi: Math.round(clamp(smooth(latest.aqi, 84, 0.05) + jitter(2), 0, 500)),
      };
    } else if (node.id === 'SN-NASH-02') {
      const rainTarget = 23 + 4 * Math.sin(elapsed / 43 + 1.8);
      const vibrationActive = Math.sin(elapsed / 9 + 1.7) > 0.86;
      reading = {
        temp: round(smooth(latest.temp, 27.1, 0.04) + jitter(0.08), 1),
        humidity: round(clamp(smooth(latest.humidity, 91.5, 0.05) + jitter(0.35), 0, 100), 1),
        rain: round(clamp(smooth(latest.rain, rainTarget, 0.14) + jitter(0.5), 0, 60), 1),
        waterLevel: round(clamp(smooth(latest.waterLevel, 47, 0.04) + jitter(0.1), 0, 150), 1),
        vibrationLevel: vibrationActive ? Math.round(55 + Math.random() * 35) : Math.round(Math.random() * 7),
        aqi: Math.round(clamp(smooth(latest.aqi, 96, 0.04) + jitter(2), 0, 500)),
      };
    } else {
      const rainTarget = 4.2 + 1.2 * Math.sin(elapsed / 75);
      reading = {
        temp: round(smooth(latest.temp, 33.5 + 0.8 * Math.sin(elapsed / 150), 0.06) + jitter(0.1), 1),
        humidity: round(clamp(smooth(latest.humidity, 71, 0.04) + jitter(0.5), 0, 100), 1),
        rain: round(clamp(smooth(latest.rain, rainTarget, 0.08) + jitter(0.2), 0, 60), 1),
        waterLevel: round(clamp(smooth(latest.waterLevel, 24, 0.03) + jitter(0.08), 0, 150), 1),
        vibrationLevel: Math.round(Math.random() * 3),
        aqi: Math.round(clamp(smooth(latest.aqi, 178 + 18 * Math.sin(elapsed / 83), 0.06) + jitter(3), 0, 500)),
      };
    }

    const battery = clamp(
      latest.battery - 0.00012 + (Math.random() < 0.025 ? 0.0009 : 0),
      3.55,
      4.18,
    );

    return {
      ...common,
      ...reading,
      vibration: reading.vibrationLevel,
      battery: round(battery, 2),
    };
  }

  tick() {
    if (!this.running) return;
    try {
      const nodes = this.store.listNodes();
      if (!nodes.length) return;
      this.packetCounter += 1;
      const readings = nodes.map((node) => this.buildReading(node));
      this.telemetryService.ingestBatch(readings, {
        gatewayId: 'GW-NSK-01',
        source: 'simulator',
        firmware: 'sentinel-gw 1.4.2',
      });
      this.lastError = null;
      this.onTick?.();
    } catch (error) {
      this.lastError = error.message;
      console.error('[simulator] tick failed:', error);
    }
  }
}

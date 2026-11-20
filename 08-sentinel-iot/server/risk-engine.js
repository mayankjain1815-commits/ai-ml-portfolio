import { clamp, riskLevelFromScore, round } from './utils.js';

export const HAZARDS = {
  flood: {
    label: 'Flood',
    alertType: 'flood',
    advisory: 'River and drainage levels are approaching or exceeding safe operating limits.',
  },
  landslide: {
    label: 'Landslide',
    alertType: 'landslide',
    advisory: 'Saturated slope conditions and ground movement have been detected.',
  },
  air: {
    label: 'Air quality',
    alertType: 'air_quality',
    advisory: 'Particulate and smoke concentration is above the public-health threshold.',
  },
  heat: {
    label: 'Extreme heat',
    alertType: 'heat',
    advisory: 'Temperature and humidity combine to create dangerous heat stress.',
  },
};

const TERRAIN_FACTORS = {
  riverine: { flood: 1.12, landslide: 0.9 },
  reservoir: { flood: 1.08, landslide: 1 },
  slope: { flood: 0.92, landslide: 1.12 },
  urban: { flood: 1.02, landslide: 0.9 },
};

/**
 * Maps a sensor value onto 0-100 between an onset and a saturation point.
 * Using onset/saturation rather than a single threshold keeps the score
 * informative while a condition is building, not just after it becomes critical.
 */
function ramp(value, onset, saturation) {
  return clamp(((Number(value) - onset) / (saturation - onset)) * 100, 0, 100);
}

function contribution(label, value, points, displayValue) {
  return {
    label,
    value: displayValue ?? String(value),
    points: round(points, 1),
  };
}

function scoreFlood(reading, context) {
  const factors = [];
  const waterPoints = ramp(reading.waterLevel, 30, 130) * 0.55;
  const rainPoints = ramp(reading.rain, 2, 40) * 0.3;
  const humidityPoints = ramp(reading.humidity, 78, 100) * 0.08;
  const waterDelta = reading.waterLevel - (context.previousWaterLevel ?? reading.waterLevel);
  const trendPoints = ramp(waterDelta, 1, 24) * 0.07;

  const terrainMultiplier = TERRAIN_FACTORS[context.terrain]?.flood ?? 1;

  factors.push(contribution('Water depth', reading.waterLevel, waterPoints * terrainMultiplier, `${round(reading.waterLevel)} cm`));
  factors.push(contribution('Rainfall intensity', reading.rain, rainPoints * terrainMultiplier, `${round(reading.rain)} mm/h`));
  if (humidityPoints >= 0.4) {
    factors.push(contribution('Saturated air', reading.humidity, humidityPoints * terrainMultiplier, `${round(reading.humidity)}%`));
  }
  if (trendPoints >= 0.4) {
    factors.push(contribution('Rising water', waterDelta, trendPoints * terrainMultiplier, `+${round(waterDelta)} cm`));
  }

  const score = clamp(
    factors.reduce((total, factor) => total + factor.points, 0),
    0,
    100,
  );

  return {
    key: 'flood',
    label: HAZARDS.flood.label,
    score: round(score),
    level: riskLevelFromScore(score),
    factors: factors.sort((a, b) => b.points - a.points),
    trend: {
      waterDelta: round(waterDelta),
      direction: waterDelta > 1 ? 'rising' : waterDelta < -1 ? 'falling' : 'steady',
    },
  };
}

function scoreLandslide(reading, context) {
  const factors = [];
  const rainPoints = ramp(reading.rain, 5, 40) * 0.5;
  const vibrationPoints = clamp(reading.vibrationLevel, 0, 100) * 0.2;
  const humidityPoints = ramp(reading.humidity, 80, 100) * 0.1;
  const slopePoints = clamp(context.slopeRisk, 0, 100) * 0.2;

  const terrainMultiplier = TERRAIN_FACTORS[context.terrain]?.landslide ?? 1;

  factors.push(contribution('Rain infiltration', reading.rain, rainPoints * terrainMultiplier, `${round(reading.rain)} mm/h`));
  if (vibrationPoints >= 0.4) {
    factors.push(
      contribution('Ground vibration', reading.vibrationLevel, vibrationPoints * terrainMultiplier, `${round(reading.vibrationLevel)}%`),
    );
  }
  if (humidityPoints >= 0.4) {
    factors.push(contribution('Soil saturation', reading.humidity, humidityPoints * terrainMultiplier, `${round(reading.humidity)}%`));
  }
  factors.push(contribution('Slope exposure', context.slopeRisk, slopePoints * terrainMultiplier, `${round(context.slopeRisk)} / 100`));

  const score = clamp(
    factors.reduce((total, factor) => total + factor.points, 0),
    0,
    100,
  );

  return {
    key: 'landslide',
    label: HAZARDS.landslide.label,
    score: round(score),
    level: riskLevelFromScore(score),
    factors: factors.sort((a, b) => b.points - a.points),
    trend: { vibrationActive: reading.vibrationLevel > 0 },
  };
}

function scoreAir(reading) {
  const factors = [];
  const aqiPoints = ramp(reading.aqi, 50, 350) * 0.85;
  const humidityPoints = ramp(reading.humidity, 80, 100) * 0.05;
  const heatPoints = ramp(reading.temp, 34, 46) * 0.1;

  factors.push(contribution('AQI', reading.aqi, aqiPoints, `${Math.round(reading.aqi)}`));
  if (humidityPoints >= 0.4) {
    factors.push(contribution('Humidity trap', reading.humidity, humidityPoints, `${round(reading.humidity)}%`));
  }
  if (heatPoints >= 0.4) {
    factors.push(contribution('Thermal load', reading.temp, heatPoints, `${round(reading.temp)}°C`));
  }

  const score = clamp(
    factors.reduce((total, factor) => total + factor.points, 0),
    0,
    100,
  );

  return {
    key: 'air',
    label: HAZARDS.air.label,
    score: round(score),
    level: riskLevelFromScore(score),
    factors: factors.sort((a, b) => b.points - a.points),
    trend: { aqi: Math.round(reading.aqi) },
  };
}

function scoreHeat(reading) {
  const factors = [];
  const heatPoints = ramp(reading.temp, 32, 46) * 0.8;
  const humidityPoints = ramp(reading.humidity, 65, 100) * 0.2;

  factors.push(contribution('Temperature', reading.temp, heatPoints, `${round(reading.temp)}°C`));
  if (humidityPoints >= 0.4) {
    factors.push(contribution('Humidity load', reading.humidity, humidityPoints, `${round(reading.humidity)}%`));
  }

  const score = clamp(
    factors.reduce((total, factor) => total + factor.points, 0),
    0,
    100,
  );

  return {
    key: 'heat',
    label: HAZARDS.heat.label,
    score: round(score),
    level: riskLevelFromScore(score),
    factors: factors.sort((a, b) => b.points - a.points),
    trend: { temp: round(reading.temp) },
  };
}

/**
 * Pure deterministic risk evaluation. The same function powers live telemetry,
 * demo simulation, API previews and tests, so an authority override can always
 * be distinguished from the underlying sensor assessment.
 */
export function assessRisk(reading, options = {}) {
  const context = {
    terrain: options.terrain ?? 'riverine',
    slopeRisk: clamp(options.slopeRisk ?? 50, 0, 100),
    previousWaterLevel: options.previousWaterLevel ?? reading.waterLevel,
  };

  const risks = [
    scoreLandslide(reading, context),
    scoreFlood(reading, context),
    scoreAir(reading),
    scoreHeat(reading),
  ];

  if (reading.sos) {
    risks.unshift({
      key: 'sos',
      label: 'Manual SOS',
      score: 100,
      level: 'severe',
      factors: [contribution('Emergency button', 100, 100, 'PRESSED')],
      trend: {},
    });
  }

  risks.sort((a, b) => b.score - a.score);
  const primary = risks[0];
  let score = primary.score;

  // Concurrent flood and slope hazards compound one another: emergency
  // planners need the combined picture, not merely the single-largest score.
  const flood = risks.find((risk) => risk.key === 'flood');
  const landslide = risks.find((risk) => risk.key === 'landslide');
  const compound = flood.score >= 50 && landslide.score >= 50;
  if (compound) score = clamp(score + 6, 0, 100);

  const level = riskLevelFromScore(score);
  const primaryHazard = HAZARDS[primary.key] ?? {
    label: primary.label,
    advisory: 'A manual emergency signal was received from this sensor node.',
  };

  return {
    score: round(score),
    level,
    primaryHazard: primary.key,
    primaryHazardLabel: primaryHazard.label,
    compound,
    headline:
      primary.key === 'sos'
        ? 'Manual SOS received'
        : `${primary.label} risk is ${level.toUpperCase()}`,
    advisory: primaryHazard.advisory,
    hazards: risks,
    topFactors: primary.factors.slice(0, 3),
    evaluatedAt: new Date().toISOString(),
  };
}

export function riskLevelToScore(level) {
  return { low: 18, moderate: 38, high: 63, severe: 88 }[level] ?? 0;
}

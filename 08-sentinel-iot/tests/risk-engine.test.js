import assert from 'node:assert/strict';
import test from 'node:test';
import { assessRisk, riskLevelToScore } from '../server/risk-engine.js';
import { riskLevelFromScore } from '../server/utils.js';
import { weatherReading } from './helpers.js';

const context = { terrain: 'riverine', slopeRisk: 38, previousWaterLevel: 32 };

test('calm conditions return a low composite risk', () => {
  const risk = assessRisk(
    weatherReading({ temp: 24, humidity: 55, rain: 0, waterLevel: 10, aqi: 40 }),
    { terrain: 'riverine', slopeRisk: 10 },
  );

  assert.equal(risk.level, 'low');
  assert.ok(risk.score < 25, `expected a low score, received ${risk.score}`);
  assert.equal(risk.compound, false);
  assert.ok(['heat', 'flood', 'landslide', 'air'].includes(risk.primaryHazard));
});

test('river gauges and rainfall drive a severe flood assessment', () => {
  const risk = assessRisk(
    weatherReading({ waterLevel: 140, rain: 38, humidity: 96, previousWaterLevel: 120 }),
    { ...context, previousWaterLevel: 120 },
  );

  assert.equal(risk.primaryHazard, 'flood');
  assert.equal(risk.level, 'severe');
  assert.ok(risk.score >= 90, `expected severe flood score, received ${risk.score}`);
  const flood = risk.hazards.find((hazard) => hazard.key === 'flood');
  assert.ok(flood.factors.length >= 3);
  assert.equal(flood.trend.direction, 'rising');
});

test('slope exposure and vibration produce a landslide warning', () => {
  const risk = assessRisk(
    weatherReading({ rain: 35, humidity: 95, vibrationLevel: 90, waterLevel: 20 }),
    { terrain: 'slope', slopeRisk: 96, previousWaterLevel: 20 },
  );

  assert.equal(risk.primaryHazard, 'landslide');
  assert.ok(risk.score >= 75);
  const landslide = risk.hazards.find((hazard) => hazard.key === 'landslide');
  assert.equal(landslide.trend.vibrationActive, true);
  assert.ok(landslide.factors.some((factor) => factor.label === 'Ground vibration'));
});

test('air quality and extreme heat each saturate their own hazard', () => {
  const air = assessRisk(weatherReading({ aqi: 420, humidity: 60, temp: 30 }), {
    ...context,
    previousWaterLevel: 32,
  });
  assert.equal(air.primaryHazard, 'air');
  assert.equal(air.level, 'severe');

  const heat = assessRisk(weatherReading({ temp: 45, humidity: 95, waterLevel: 10 }), {
    terrain: 'urban',
    slopeRisk: 10,
    previousWaterLevel: 10,
  });
  assert.equal(heat.primaryHazard, 'heat');
  assert.equal(heat.level, 'severe');
});

test('concurrent flood and slope hazards compound the composite score', () => {
  const risk = assessRisk(
    weatherReading({
      waterLevel: 100,
      rain: 30,
      humidity: 90,
      vibrationLevel: 60,
      previousWaterLevel: 90,
      aqi: 50,
    }),
    { terrain: 'riverine', slopeRisk: 80, previousWaterLevel: 90 },
  );

  const flood = risk.hazards.find((hazard) => hazard.key === 'flood');
  const landslide = risk.hazards.find((hazard) => hazard.key === 'landslide');
  assert.ok(flood.score >= 50);
  assert.ok(landslide.score >= 50);
  assert.equal(risk.compound, true);
  assert.ok(risk.score > Math.max(flood.score, landslide.score));
});

test('manual SOS always outranks sensor hazards', () => {
  const risk = assessRisk(
    weatherReading({ sos: true, waterLevel: 120, rain: 20, humidity: 95 }),
    { ...context, previousWaterLevel: 110 },
  );

  assert.equal(risk.primaryHazard, 'sos');
  assert.equal(risk.primaryHazardLabel, 'Manual SOS');
  assert.equal(risk.score, 100);
  assert.equal(risk.level, 'severe');
  assert.match(risk.headline, /Manual SOS/);
});

test('risk level thresholds are stable and monotonic', () => {
  assert.equal(riskLevelFromScore(0), 'low');
  assert.equal(riskLevelFromScore(24.9), 'low');
  assert.equal(riskLevelFromScore(25), 'moderate');
  assert.equal(riskLevelFromScore(49.9), 'moderate');
  assert.equal(riskLevelFromScore(50), 'high');
  assert.equal(riskLevelFromScore(74.9), 'high');
  assert.equal(riskLevelFromScore(75), 'severe');
  assert.equal(riskLevelFromScore(100), 'severe');
  for (const level of ['low', 'moderate', 'high', 'severe']) {
    assert.ok(riskLevelToScore(level) >= 0);
    assert.ok(riskLevelToScore(level) <= 100);
  }
});

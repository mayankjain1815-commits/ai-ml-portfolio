import { z } from 'zod';
import { normalizeVibration } from './utils.js';

const nullableCoordinate = (minimum, maximum) =>
  z
    .number()
    .min(minimum)
    .max(maximum)
    .nullable()
    .optional();

export const telemetrySchema = z
  .object({
    nodeId: z.string().trim().min(3).max(64),
    lat: nullableCoordinate(-90, 90),
    lon: nullableCoordinate(-180, 180),
    temp: z.number().min(-40).max(85),
    humidity: z.number().min(0).max(100),
    rain: z.number().min(0).max(500),
    waterLevel: z.number().min(0).max(1500),
    vibration: z.union([z.boolean(), z.number().min(0).max(100)]),
    aqi: z.number().min(0).max(1000),
    sos: z.boolean().optional().default(false),
    battery: z.number().min(0).max(5.5),
    rssi: z.number().min(-160).max(0).optional().default(-80),
    snr: z.number().min(-40).max(40).optional().default(0),
    timestamp: z.coerce.date().optional(),
    packetId: z.string().trim().max(100).optional(),
  })
  .strict()
  .transform((reading) => {
    const vibrationLevel = normalizeVibration(reading.vibration);
    return {
      ...reading,
      lat: reading.lat ?? null,
      lon: reading.lon ?? null,
      vibration: vibrationLevel > 0,
      vibrationLevel,
      timestamp: (reading.timestamp ?? new Date()).toISOString(),
    };
  });

export const gatewayBatchSchema = z
  .object({
    gatewayId: z.string().trim().min(3).max(64),
    firmware: z.string().trim().max(100).optional(),
    timestamp: z.coerce.date().optional(),
    readings: z.array(telemetrySchema).min(1).max(24),
  })
  .strict();

export const commandSchemas = {
  evacuation: z
    .object({
      nodeId: z.string().trim().max(64).nullable().optional(),
      reason: z.string().trim().min(5).max(280),
      operator: z.string().trim().min(2).max(80).optional(),
    })
    .strict(),
  override: z
    .object({
      nodeId: z.string().trim().min(3).max(64),
      level: z.enum(['low', 'moderate', 'high', 'severe']),
      note: z.string().trim().min(4).max(280),
      durationMinutes: z.number().int().min(5).max(1440).optional().default(60),
      operator: z.string().trim().min(2).max(80).optional(),
    })
    .strict(),
  acknowledge: z
    .object({
      operator: z.string().trim().min(2).max(80).optional(),
    })
    .strict(),
  siren: z
    .object({
      enabled: z.boolean(),
      operator: z.string().trim().min(2).max(80).optional(),
    })
    .strict(),
  sosTest: z
    .object({
      nodeId: z.string().trim().min(3).max(64),
      operator: z.string().trim().min(2).max(80).optional(),
    })
    .strict(),
};

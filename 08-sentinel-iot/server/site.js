export const SITE = {
  code: 'SECTOR-04',
  name: 'Nashik Basin',
  district: 'Nashik, Maharashtra',
  organization: 'District Disaster Management Authority',
  center: { lat: 20.012, lon: 73.816 },
  bounds: [
    [19.972, 73.748],
    [20.072, 73.872],
  ],
};

export const NODES = [
  {
    id: 'SN-NASH-01',
    name: 'Godavari Ghat',
    location: 'Godavari riverfront, Panchavati',
    district: SITE.district,
    lat: 19.9975,
    lon: 73.7898,
    terrain: 'riverine',
    slopeRisk: 38,
    population: 18400,
    gatewayId: 'GW-NSK-01',
  },
  {
    id: 'SN-NASH-02',
    name: 'Panchavati Ridge',
    location: 'North ridge settlement, Panchavati',
    district: SITE.district,
    lat: 20.0234,
    lon: 73.812,
    terrain: 'slope',
    slopeRisk: 96,
    population: 9200,
    gatewayId: 'GW-NSK-01',
  },
  {
    id: 'SN-NASH-03',
    name: 'Darna Spillway',
    location: 'Darna reservoir outlet, Nashik East',
    district: SITE.district,
    lat: 20.0488,
    lon: 73.8425,
    terrain: 'reservoir',
    slopeRisk: 44,
    population: 5600,
    gatewayId: 'GW-NSK-01',
  },
];

export const GATEWAY = {
  id: 'GW-NSK-01',
  name: 'Central LoRa Gateway',
  location: 'DDMA control room, Nashik',
  firmware: 'sentinel-gw 1.4.2',
};

export const NODE_SEED_PROFILE = {
  'SN-NASH-01': {
    start: { temp: 27.2, humidity: 84, rain: 6.4, waterLevel: 91, vibrationLevel: 0, aqi: 72, battery: 3.98 },
    end: { temp: 28.4, humidity: 94, rain: 26.2, waterLevel: 128.4, vibrationLevel: 0, aqi: 84, battery: 3.82 },
  },
  'SN-NASH-02': {
    start: { temp: 26.8, humidity: 82, rain: 4.8, waterLevel: 33, vibrationLevel: 12, aqi: 76, battery: 4.03 },
    end: { temp: 27.1, humidity: 91, rain: 18.6, waterLevel: 47.2, vibrationLevel: 100, aqi: 96, battery: 3.79 },
  },
  'SN-NASH-03': {
    start: { temp: 31.4, humidity: 69, rain: 2.1, waterLevel: 21.5, vibrationLevel: 0, aqi: 132, battery: 4.12 },
    end: { temp: 33.4, humidity: 71, rain: 4.2, waterLevel: 24.2, vibrationLevel: 0, aqi: 187, battery: 4.06 },
  },
};

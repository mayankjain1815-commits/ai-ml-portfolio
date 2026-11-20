import { SITE } from './site.js';

export const SECTORS = {
  'SECTOR-01': {
    code: 'SECTOR-01',
    name: 'Godavari Basin',
    district: 'Maharashtra',
    organization: 'District Disaster Management Authority',
    center: { lat: 19.8762, lon: 75.3433 },
    bounds: [
      [19.8, 75.25],
      [19.95, 75.45],
    ],
  },
  'SECTOR-02': {
    code: 'SECTOR-02',
    name: 'Tapi Basin',
    district: 'Gujarat',
    organization: 'District Disaster Management Authority',
    center: { lat: 21.1702, lon: 72.8311 },
    bounds: [
      [21.1, 72.75],
      [21.25, 72.9],
    ],
  },
  'SECTOR-03': {
    code: 'SECTOR-03',
    name: 'Krishna Basin',
    district: 'Karnataka',
    organization: 'District Disaster Management Authority',
    center: { lat: 16.5062, lon: 80.648 },
    bounds: [
      [16.45, 80.58],
      [16.56, 80.72],
    ],
  },
  'SECTOR-04': SITE,
};

export function getSector(code) {
  return SECTORS[code] || SITE;
}

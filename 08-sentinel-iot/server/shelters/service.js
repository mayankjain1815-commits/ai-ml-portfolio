import { createId } from '../utils.js';

export const SHELTERS = [
  { id: 'SH-001', name: 'Panchavati Community Shelter', lat: 20.005, lon: 73.796, capacity: 500, occupied: 0, type: 'school', facilities: ['food', 'water', 'medical', 'sanitation'] },
  { id: 'SH-002', name: 'Nashik Road Relief Camp', lat: 19.984, lon: 73.817, capacity: 800, occupied: 0, type: 'hall', facilities: ['food', 'water', 'medical'] },
  { id: 'SH-003', name: 'Darna Upper Plateau Shelter', lat: 20.058, lon: 73.847, capacity: 300, occupied: 0, type: 'school', facilities: ['food', 'water'] },
];

export class ShelterService {
  findNearest(lat, lon, maxDistanceKm = 50) {
    const results = SHELTERS.map(shelter => {
      const dist = this.haversineDistance(lat, lon, shelter.lat, shelter.lon);
      return { ...shelter, distanceKm: Math.round(dist * 100) / 100, available: shelter.capacity - shelter.occupied };
    }).filter(s => s.distanceKm <= maxDistanceKm);
    results.sort((a,b) => a.distanceKm - b.distanceKm);
    return results;
  }

  getRoute(fromLat, fromLon, toShelter) {
    const dist = this.haversineDistance(fromLat, fromLon, toShelter.lat, toShelter.lon);
    const timeMin = Math.round((dist / 30) * 60); // assuming 30 km/h in emergency
    return {
      from: { lat: fromLat, lon: fromLon },
      to: toShelter,
      distanceKm: Math.round(dist * 100) / 100,
      estimatedTimeMin: timeMin,
      route: 'shortest',
      instructions: [
        `Head towards ${toShelter.name}`,
        `Distance: ${Math.round(dist * 100)/100} km, ETA: ~${timeMin} min`,
        'Follow designated evacuation route',
        'Stay on higher ground if possible'
      ]
    };
  }

  haversineDistance(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dLat = this.toRad(lat2 - lat1);
    const dLon = this.toRad(lon2 - lon1);
    const a = Math.sin(dLat/2)*Math.sin(dLat/2) +
              Math.cos(this.toRad(lat1))*Math.cos(this.toRad(lat2)) *
              Math.sin(dLon/2)*Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
  }

  toRad(deg) { return deg * Math.PI / 180; }
}

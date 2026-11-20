import express from 'express';
import { ShelterService } from '../shelters/service.js';

const router = express.Router();
const shelterService = new ShelterService();

router.get('/safe-route', (req, res) => {
  const lat = parseFloat(req.query.lat);
  const lon = parseFloat(req.query.lon);
  if (isNaN(lat) || isNaN(lon)) {
    return res.status(400).json({ ok: false, error: 'lat and lon required' });
  }
  
  const shelters = shelterService.findNearest(lat, lon);
  const safest = shelters[0] || { id: 'SH-DEF', name: 'Nearest Designated Shelter', lat: lat + 0.01, lon: lon + 0.01, distanceKm: 0.5 };
  
  const googleMapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${safest.lat},${safest.lon}&travelmode=driving`;
  const appleMapsUrl = `http://maps.apple.com/?daddr=${safest.lat},${safest.lon}&dirflg=d`;
  
  const route = shelterService.getRoute(lat, lon, safest);
  
  res.json({ 
    ok: true, 
    data: { 
      currentLocation: { lat, lon },
      safestShelter: safest,
      route,
      directions: {
        googleMaps: googleMapsUrl,
        appleMaps: appleMapsUrl,
        waze: `https://waze.com/ul?ll=${safest.lat},${safest.lon}&navigate=yes`
      }
    } 
  });
});

router.get('/evacuation-zones', (req, res) => {
  res.json({
    ok: true,
    data: [
      { id: 'EZ-1', name: 'Godavari Lowlands', risk: 'severe', evacuationRequired: true, shelters: ['SH-001'] },
      { id: 'EZ-2', name: 'Panchavati Ridge', risk: 'high', evacuationRequired: true, shelters: ['SH-001', 'SH-002'] },
      { id: 'EZ-3', name: 'Darna Spillway', risk: 'moderate', evacuationRequired: false, shelters: ['SH-003'] }
    ]
  });
});

export default router;

router.get('/emergency-directions', (req, res) => {
  const lat = parseFloat(req.query.lat);
  const lon = parseFloat(req.query.lon);
  const mode = req.query.mode || 'driving';
  if (isNaN(lat) || isNaN(lon)) {
    return res.status(400).json({ ok: false, error: 'lat and lon required' });
  }
  
  const shelters = shelterService.findNearest(lat, lon);
  const safest = shelters[0] || { id: 'SH-DEF', name: 'Emergency Shelter', lat: lat + 0.015, lon: lon + 0.015 };
  
  res.json({
    ok: true,
    data: {
      emergency: true,
      priority: 'HIGH',
      safestShelter: safest,
      directions: {
        googleMaps: `https://www.google.com/maps/dir/?api=1&origin=${lat},${lon}&destination=${safest.lat},${safest.lon}&travelmode=${mode}&avoid=tolls|highways`,
        appleMaps: `http://maps.apple.com/?saddr=${lat},${lon}&daddr=${safest.lat},${safest.lon}&dirflg=d`,
        waze: `https://waze.com/ul?ll=${safest.lat},${safest.lon}&from=${lat},${lon}&navigate=yes`,
        osm: `https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${lat}%2C${lon}%3B${safest.lat}%2C${safest.lon}`
      },
      instructions: [
        'DO NOT DELAY - Evacuate immediately if ordered',
        `Proceed to ${safest.name}`,
        'Follow main roads, avoid low-lying areas',
        'Keep emergency supplies ready',
        'Call 112 if you need assistance'
      ],
      estimatedTime: shelterService.getRoute(lat, lon, safest).estimatedTimeMin + ' min'
    }
  });
});

router.post('/request-evacuation', (req, res) => {
  const { lat, lon, name, phone } = req.body || {};
  res.json({
    ok: true,
    data: {
      requestId: 'EVAC-' + Date.now(),
      status: 'received',
      message: 'Evacuation request received. Help is on the way.',
      dispatchedTo: 'Nearest Response Team'
    }
  });
});

router.get('/offline-kit', (req, res) => {
  const allShelters = [
    { id: 'SH-001', name: 'Nashik Civil Hospital Relief Camp', lat: 20.0110, lon: 73.7903, capacity: 500, type: 'hospital', contact: '+91-253-257-8901' },
    { id: 'SH-002', name: 'Panchavati School Evacuation Center', lat: 20.0067, lon: 73.7910, capacity: 300, type: 'school', contact: '+91-253-259-1234' },
    { id: 'SH-003', name: 'Dindori Road Community Hall', lat: 20.0205, lon: 73.8102, capacity: 250, type: 'community', contact: '+91-253-262-5678' },
    { id: 'SH-004', name: 'Godavari Ghat Relief Camp', lat: 19.9950, lon: 73.7800, capacity: 400, type: 'camp', contact: '+91-253-258-9012' },
    { id: 'SH-005', name: 'Satpur Industrial Area Shelter', lat: 20.0025, lon: 73.7550, capacity: 350, type: 'warehouse', contact: '+91-253-261-3456' }
  ];

  res.json({
    ok: true,
    data: {
      shelters: allShelters,
      zones: [
        { id: 'EZ-1', name: 'Godavari Lowlands', risk: 'severe', evacuationRequired: true },
        { id: 'EZ-2', name: 'Panchavati Ridge', risk: 'high', evacuationRequired: true },
        { id: 'EZ-3', name: 'Darna Spillway', risk: 'moderate', evacuationRequired: false }
      ],
      emergencyContacts: {
        police: '100',
        fire: '101',
        ambulance: '102',
        disasterHelpline: '108',
        ndma: '1078'
      },
      instructions: [
        'Stay calm and follow evacuation orders',
        'Take only essential items (ID, medicines, water)',
        'Avoid low-lying areas and riverbanks',
        'Do not walk through flood water',
        'Switch off gas and electricity if safe',
        'Keep your phone on for emergency alerts',
        'Head to nearest designated shelter immediately'
      ],
      downloadTime: new Date().toISOString(),
      version: '1.0'
    }
  });
});

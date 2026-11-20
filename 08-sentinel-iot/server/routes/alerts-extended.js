import express from 'express';
import { ShelterService } from '../shelters/service.js';
import { NotificationService } from '../notifications/service.js';
import { authenticateToken } from '../middleware/auth.js';

const router = express.Router();
const shelterService = new ShelterService();

router.get('/shelters/nearest', (req, res) => {
  const lat = parseFloat(req.query.lat);
  const lon = parseFloat(req.query.lon);
  if (isNaN(lat) || isNaN(lon)) {
    return res.status(400).json({ ok: false, error: 'lat and lon required' });
  }
  const shelters = shelterService.findNearest(lat, lon);
  res.json({ ok: true, data: shelters });
});

router.get('/shelters/route', (req, res) => {
  const lat = parseFloat(req.query.lat);
  const lon = parseFloat(req.query.lon);
  const shelterId = req.query.shelterId;
  if (isNaN(lat) || isNaN(lon) || !shelterId) {
    return res.status(400).json({ ok: false, error: 'lat, lon, shelterId required' });
  }
  const shelter = shelterService.findNearest(lat, lon).find(s => s.id === shelterId) || 
                  { id: shelterId, name: 'Shelter', lat: lat+0.01, lon: lon+0.01 };
  const route = shelterService.getRoute(lat, lon, shelter);
  res.json({ ok: true, data: route });
});

export default router;

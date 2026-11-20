import express from 'express';
import { generateToken } from '../middleware/auth.js';
import { authLimiter } from '../middleware/security.js';

const router = express.Router();

const USERS = {
  common: [
    { id: 100, username: 'citizen', password: 'citizen123', role: 'citizen', name: 'General Public' }
  ],
  employee: [
    { id: 200, username: 'employee', password: 'employee123', role: 'employee', name: 'Field Employee', dept: 'Operations' }
  ],
  owner: [
    { id: 999, username: 'owner', password: 'owner123', role: 'owner', name: 'System Owner', dept: 'Management' }
  ],
  admin: [
    { id: 1, username: 'admin', password: 'admin', role: 'admin', name: 'Admin' }
  ]
};

router.post('/login/:type', authLimiter, async (req, res) => {
  const { type } = req.params;
  const { username, password } = req.body;
  
  const userList = USERS[type] || [];
  const user = userList.find(u => u.username === username && u.password === password);
  
  if (!user) {
    return res.status(401).json({ ok: false, error: 'Invalid credentials' });
  }
  
  const token = generateToken({ id: user.id, username: user.username, role: user.role });
  res.json({ 
    ok: true, 
    token, 
    user: { username: user.username, role: user.role, name: user.name, dept: user.dept }
  });
});

router.get('/types', (req, res) => {
  res.json({
    ok: true,
    data: [
      { type: 'common', label: 'Citizen/Public', description: 'View alerts and evacuation routes' },
      { type: 'employee', label: 'Employee/Field Staff', description: 'Monitor and report' },
      { type: 'admin', label: 'Admin/Authority', description: 'Full command access' },
      { type: 'owner', label: 'Owner/Super Admin', description: 'System management' }
    ]
  });
});

export default router;

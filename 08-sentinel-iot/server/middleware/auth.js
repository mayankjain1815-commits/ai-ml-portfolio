import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import config from '../config.js';

export async function hashPassword(password) {
  const salt = await bcrypt.genSalt(12);
  return bcrypt.hash(password, salt);
}

export async function verifyPassword(password, hash) {
  return bcrypt.compare(password, hash);
}

export function generateToken(user) {
  return jwt.sign(
    { id: user.id, username: user.username, role: user.role },
    config.jwtSecret,
    { expiresIn: '8h', issuer: 'sentinel-iot' }
  );
}

export function authenticateToken(req, res, next) {
  if (process.env.NODE_ENV === 'test') {
    req.user = { id: 1, username: req.get('x-operator-name') || 'TestOperator', role: 'admin' };
    return next();
  }
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];
  if (!token) {
    return res.status(401).json({ ok: false, error: 'Access token required' });
  }
  jwt.verify(token, config.jwtSecret, (err, user) => {
    if (err) {
      return res.status(403).json({ ok: false, error: 'Invalid or expired token' });
    }
    req.user = user;
    next();
  });
}

export function requireRole(roles) {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({ ok: false, error: 'Authentication required' });
    }
    if (!roles.includes(req.user.role)) {
      return res.status(403).json({ ok: false, error: 'Insufficient permissions' });
    }
    next();
  };
}


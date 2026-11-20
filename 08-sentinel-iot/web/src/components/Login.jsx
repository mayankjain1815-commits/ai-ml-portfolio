import { useState } from 'react';
import { Shield, Info, ChevronDown, ChevronUp } from 'lucide-react';
import { login } from '../lib/api.js';
import { setAuth } from '../lib/auth.js';

const DEMO_CREDENTIALS = [
  { role: 'Admin', username: 'admin', password: 'admin', desc: 'Full command & control' },
  { role: 'Operator', username: 'operator', password: 'operator', desc: 'Monitoring & alerts' },
  { role: 'Owner', username: 'owner', password: 'owner123', desc: 'System management' },
  { role: 'Employee', username: 'employee', password: 'employee123', desc: 'Field operations' },
  { role: 'Citizen', username: 'citizen', password: 'citizen123', desc: 'Public access' },
];

export function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showGuide, setShowGuide] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await login(username, password);
      if (res.ok && res.token) {
        setAuth(res.token, res.user);
        onLogin(res.user);
      } else {
        setError(res.error || 'Login failed');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fillCreds = (u, p) => {
    setUsername(u);
    setPassword(p);
    setError('');
  };

  return (
    <div className="login-screen">
      <div className="login-card" style={{ maxWidth: '480px' }}>
        <div className="login-header">
          <div className="login-logo">
            <Shield size={32} />
          </div>
          <h1>SENTINEL · Disaster Command</h1>
          <p>IoT Early Warning & Emergency Response System</p>
        </div>
        <form onSubmit={handleSubmit} className="login-form">
          <div className="login-field">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              placeholder="Enter your username"
              required
            />
          </div>
          <div className="login-field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              placeholder="Enter your password"
              required
            />
          </div>
          {error && <div className="login-error">{error}</div>}
          <button type="submit" className="login-button" disabled={loading}>
            {loading ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>

        <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'rgba(234,170,0,0.1)', borderRadius: '8px', border: '1px solid rgba(234,170,0,0.3)' }}>
          <button 
            onClick={() => setShowGuide(!showGuide)} 
            style={{ width: '100%', background: 'transparent', border: 'none', color: '#EAAA00', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontWeight: '600' }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Info size={18} /> New User? Demo Credentials</span>
            {showGuide ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </button>
          
          {showGuide && (
            <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {DEMO_CREDENTIALS.map((cred) => (
                <button
                  key={cred.username}
                  onClick={() => fillCreds(cred.username, cred.password)}
                  style={{ textAlign: 'left', padding: '0.5rem', background: 'rgba(58,15,52,0.5)', border: '1px solid rgba(221,211,232,0.2)', borderRadius: '6px', cursor: 'pointer', color: 'inherit' }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong>{cred.role}</strong>
                    <span style={{ fontSize: '0.875rem', opacity: 0.8 }}>{cred.username} / {cred.password}</span>
                  </div>
                  <div style={{ fontSize: '0.75rem', opacity: 0.7, marginTop: '0.25rem' }}>{cred.desc}</div>
                </button>
              ))}
              <div style={{ fontSize: '0.75rem', opacity: 0.7, textAlign: 'center', marginTop: '0.5rem' }}>
                Click any card to auto-fill credentials
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

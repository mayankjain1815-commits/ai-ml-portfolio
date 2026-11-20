import { X, User, Shield, LogOut, BookOpen, Map, Bell, Navigation, WifiOff } from 'lucide-react';
import { getUser, clearAuth } from '../lib/auth.js';

export function ProfileModal({ open, onClose, onLogout }) {
  if (!open) return null;
  const user = getUser();

  const handleLogout = () => {
    clearAuth();
    onLogout();
    onClose();
  };

  const getAccessLevel = (role) => {
    if (role === 'admin' || role === 'owner') return 'Full Authority';
    if (role === 'employee') return 'Field Operations';
    if (role === 'operator') return 'Monitoring Access';
    return 'Public Access';
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="profile-modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '520px' }}>
        <div className="profile-modal__header">
          <h2>User Profile & Guide</h2>
          <button className="icon-button" onClick={onClose} aria-label="Close">
            <X size={20} />
          </button>
        </div>
        <div className="profile-modal__body" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
          <div className="profile-avatar">
            <User size={48} />
          </div>
          <div className="profile-info">
            <div className="profile-row">
              <span className="profile-label">Username</span>
              <span className="profile-value">{user?.username || 'Unknown'}</span>
            </div>
            <div className="profile-row">
              <span className="profile-label">Role</span>
              <span className="profile-value profile-role">
                <Shield size={14} />
                {user?.role || 'User'}
              </span>
            </div>
            <div className="profile-row">
              <span className="profile-label">Access Level</span>
              <span className="profile-value">{getAccessLevel(user?.role)}</span>
            </div>
          </div>

          <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'rgba(221,211,232,0.05)', borderRadius: '8px' }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', margin: '0 0 0.75rem 0', fontSize: '1rem' }}>
              <BookOpen size={18} /> How to Use This Website
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.875rem' }}>
              <div>
                <strong style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Map size={14} /> Overview</strong>
                <p style={{ margin: '0.25rem 0 0 1.25rem', opacity: 0.8 }}>Live dashboard with all sensors, risk levels, and alerts</p>
              </div>
              <div>
                <strong style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Map size={14} /> Map View</strong>
                <p style={{ margin: '0.25rem 0 0 1.25rem', opacity: 0.8 }}>Interactive map showing node locations with risk zones</p>
              </div>
              <div>
                <strong style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Bell size={14} /> Alerts</strong>
                <p style={{ margin: '0.25rem 0 0 1.25rem', opacity: 0.8 }}>All active warnings - acknowledge as authority</p>
              </div>
              <div>
                <strong style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Navigation size={14} /> Evacuation (Overview Panel)</strong>
                <p style={{ margin: '0.25rem 0 0 1.25rem', opacity: 0.8 }}>Get safest route to shelter with Google/Apple/Waze/OSM directions. Download offline kit for no-internet use.</p>
              </div>
              <div>
                <strong style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}><WifiOff size={14} /> Offline Mode</strong>
                <p style={{ margin: '0.25rem 0 0 1.25rem', opacity: 0.8 }}>Download offline evacuation kit while online. Works during network outages with cached shelters & routes.</p>
              </div>
            </div>
          </div>

          <div style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(234,170,0,0.1)', borderRadius: '8px', border: '1px solid rgba(234,170,0,0.3)' }}>
            <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '0.875rem', color: '#EAAA00' }}>Quick Tips</h3>
            <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.8125rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              <li>Click DDMA indicator for site info</li>
              <li>Use sector switcher to change regions (Admin only)</li>
              <li>Command Console for authority actions</li>
              <li>Always download offline kit before disaster season</li>
            </ul>
          </div>
        </div>
        <div className="profile-modal__footer">
          <button className="profile-logout" onClick={handleLogout}>
            <LogOut size={18} />
            Sign Out
          </button>
        </div>
      </div>
    </div>
  );
}

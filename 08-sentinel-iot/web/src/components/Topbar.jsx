import { Bell, Menu, Shield } from 'lucide-react';
import { formatClock, formatDate } from '../lib/format.js';
import { getUser } from '../lib/auth.js';

const VIEW_TITLES = {
  overview: {
    eyebrow: 'Operational picture',
    title: 'Regional situation',
    description: 'Live sensor intelligence and risk posture',
  },
  map: {
    eyebrow: 'Geospatial intelligence',
    title: 'Affected areas',
    description: 'GPS-located nodes and projected impact envelopes',
  },
  alerts: {
    eyebrow: 'Emergency communications',
    title: 'Active alerts',
    description: 'Automated warnings, manual SOS and authority broadcasts',
  },
  incidents: {
    eyebrow: 'Operational record',
    title: 'Incident log',
    description: 'Searchable audit trail of warnings and field events',
  },
  command: {
    eyebrow: 'Authority access',
    title: 'Command console',
    description: 'Override risk, issue evacuation and manage node health',
  },
};

function connectionCopy(connection) {
  if (connection === 'live') return { label: 'Live feed', detail: 'WebSocket' };
  if (connection === 'polling') return { label: 'Polling', detail: '12s refresh' };
  if (connection === 'offline') return { label: 'Offline', detail: 'Retrying' };
  return { label: 'Connecting', detail: 'Syncing' };
}

export function Topbar({ view, snapshot, connection, onMenu, onOpenAlerts, onOpenProfile }) {
  const meta = VIEW_TITLES[view] ?? VIEW_TITLES.overview;
  const connectionState = connectionCopy(connection);
  const unacknowledged = snapshot?.summary?.unacknowledgedAlerts ?? 0;
  const user = getUser();
  const operator = user?.username || snapshot?.meta?.operator || 'Duty Officer';
  const role = user?.role || 'operator';
  const initials = operator
    .replace(/^Duty Officer\s+/i, '')
    .split(/[\s_-]+/)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  return (
    <header className="topbar">
      <div className="topbar__left">
        <button className="icon-button topbar__menu" onClick={onMenu} aria-label="Open navigation">
          <Menu size={20} />
        </button>
        <div className="topbar__title-block">
          <span className="topbar__eyebrow">{meta.eyebrow}</span>
          <div className="topbar__title-row">
            <h1>{meta.title}</h1>
            <span className="topbar__description">{meta.description}</span>
          </div>
        </div>
      </div>

      <div className="topbar__right">
        <div className={`connection-pill connection-pill--${connection}`}>
          <span className="connection-pill__dot" />
          <span>{connectionState.label}</span>
          <span className="connection-pill__detail">{connectionState.detail}</span>
        </div>

        <div className="topbar__clock">
          <span className="topbar__clock-time">{formatClock()}</span>
          <span className="topbar__clock-date">{formatDate(new Date())} · IST</span>
        </div>

        <button
          className={`topbar__alert-button ${unacknowledged ? 'topbar__alert-button--active' : ''}`}
          onClick={onOpenAlerts}
          aria-label={`${unacknowledged} unacknowledged alerts`}
        >
          <Bell size={18} />
          {unacknowledged ? <span className="topbar__alert-count">{unacknowledged}</span> : null}
        </button>

        <button className="operator-chip" onClick={onOpenProfile} aria-label="Open profile" style={{ cursor: 'pointer', background: 'transparent', border: 'none', textAlign: 'left' }}>
          <span className="operator-chip__avatar">{initials || 'DO'}</span>
          <span className="operator-chip__copy">
            <span className="operator-chip__name">{operator}</span>
            <span className="operator-chip__role">
              <Shield size={10} />
              {role === 'admin' ? 'Admin authority' : 'Duty authority'}
            </span>
          </span>
        </button>
      </div>
    </header>
  );
}

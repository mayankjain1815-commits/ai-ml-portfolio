import {
  AlertTriangle,
  Command,
  LayoutDashboard,
  Map,
  RadioTower,
  ScrollText,
  ShieldCheck,
  Wifi,
  X,
} from 'lucide-react';
import { SentinelMark } from './Logo.jsx';
import { formatRelative, riskLabel } from '../lib/format.js';

const PRIMARY_NAV = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard, hint: 'Operational picture' },
  { id: 'map', label: 'Live map', icon: Map, hint: 'Affected areas' },
  { id: 'alerts', label: 'Alerts', icon: AlertTriangle, hint: 'Warning stream', badge: 'alerts' },
  { id: 'incidents', label: 'Incident log', icon: ScrollText, hint: 'Field record' },
  { id: 'command', label: 'Command', icon: Command, hint: 'Authority console' },
];

function SystemRow({ label, value, tone = 'quiet', detail }) {
  return (
    <div className="system-row">
      <span className={`system-row__dot system-row__dot--${tone}`} />
      <div>
        <span className="system-row__label">{label}</span>
        <span className="system-row__value">{value}</span>
        {detail ? <span className="system-row__detail">{detail}</span> : null}
      </div>
    </div>
  );
}

export function Sidebar({ view, onNavigate, snapshot, open, onClose }) {
  const summary = snapshot?.summary;
  const gateway = snapshot?.gateway;
  const alerts = snapshot?.alerts ?? [];
  const severe = alerts.find((alert) => alert.severity === 'severe' && alert.status === 'active');
  const peakNode = snapshot?.nodes?.find((node) => node.id === summary?.peakNode?.id);

  const navigate = (nextView) => {
    onNavigate(nextView);
    onClose?.();
  };

  return (
    <>
      <aside className={`sidebar ${open ? 'sidebar--open' : ''}`} aria-label="Primary navigation">
        <div className="sidebar__brand">
          <button
            onClick={() => {
              onNavigate('overview');
              onClose?.();
            }}
            aria-label="Go to overview"
            style={{ background: 'transparent', border: 'none', padding: 0, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.9rem' }}
          >
            <SentinelMark size={44} />
            <div className="sidebar__brand-copy">
              <span className="sidebar__wordmark">SENTINEL</span>
              <span className="sidebar__tagline">Disaster command</span>
            </div>
          </button>
          <button className="sidebar__close icon-button" onClick={onClose} aria-label="Close navigation">
            <X size={18} />
          </button>
        </div>

        <div className="sidebar__sector">
          <span className="micro-label">Active sector</span>
          <div className="sidebar__sector-row">
            <span className="sidebar__sector-code">{snapshot?.meta?.site?.code ?? 'SECTOR-04'}</span>
            <span className="status-dot status-dot--pulse" />
          </div>
          <strong>{snapshot?.meta?.site?.name ?? 'Nashik Basin'}</strong>
          <span className="sidebar__sector-detail">{snapshot?.meta?.site?.district ?? 'Maharashtra'}</span>
          <div className="sidebar__sectors" style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            <span className="micro-label">Other sectors</span>
            <button
              className="nav-item"
              style={{ padding: '0.5rem 0.6rem' }}
              onClick={async () => {
                try {
                  const token = localStorage.getItem('sentinel_token');
                  await fetch('/api/site/switch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
                    body: JSON.stringify({ code: 'SECTOR-01' }),
                  });
                  window.location.reload();
                } catch (e) {
                  console.error(e);
                }
              }}
            >
              <span className="nav-item__copy">
                <span className="nav-item__label">SECTOR-01 · Godavari Basin</span>
                <span className="nav-item__hint">Maharashtra</span>
              </span>
            </button>
            <button
              className="nav-item"
              style={{ padding: '0.5rem 0.6rem' }}
              onClick={async () => {
                try {
                  const token = localStorage.getItem('sentinel_token');
                  await fetch('/api/site/switch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
                    body: JSON.stringify({ code: 'SECTOR-02' }),
                  });
                  window.location.reload();
                } catch (e) {
                  console.error(e);
                }
              }}
            >
              <span className="nav-item__copy">
                <span className="nav-item__label">SECTOR-02 · Tapi Basin</span>
                <span className="nav-item__hint">Gujarat</span>
              </span>
            </button>
            <button
              className="nav-item"
              style={{ padding: '0.5rem 0.6rem' }}
              onClick={async () => {
                try {
                  const token = localStorage.getItem('sentinel_token');
                  await fetch('/api/site/switch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
                    body: JSON.stringify({ code: 'SECTOR-03' }),
                  });
                  window.location.reload();
                } catch (e) {
                  console.error(e);
                }
              }}
            >
              <span className="nav-item__copy">
                <span className="nav-item__label">SECTOR-03 · Krishna Basin</span>
                <span className="nav-item__hint">Karnataka</span>
              </span>
            </button>
            <button
              className="nav-item"
              style={{ padding: '0.5rem 0.6rem' }}
              onClick={async () => {
                try {
                  const token = localStorage.getItem('sentinel_token');
                  await fetch('/api/site/switch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
                    body: JSON.stringify({ code: 'SECTOR-04' }),
                  });
                  window.location.reload();
                } catch (e) {
                  console.error(e);
                }
              }}
            >
              <span className="nav-item__copy">
                <span className="nav-item__label">SECTOR-04 · Nashik Basin</span>
                <span className="nav-item__hint">Maharashtra</span>
              </span>
            </button>
          </div>
        </div>

        <nav className="sidebar__nav">
          <span className="micro-label sidebar__nav-label">Operations</span>
          {PRIMARY_NAV.slice(0, 3).map((item) => {
            const Icon = item.icon;
            const badgeValue =
              item.badge === 'alerts' && summary?.unacknowledgedAlerts
                ? summary.unacknowledgedAlerts
                : null;
            return (
              <button
                key={item.id}
                className={`nav-item ${view === item.id ? 'nav-item--active' : ''}`}
                onClick={() => navigate(item.id)}
                aria-current={view === item.id ? 'page' : undefined}
              >
                <Icon size={18} strokeWidth={1.8} />
                <span className="nav-item__copy">
                  <span className="nav-item__label">{item.label}</span>
                  <span className="nav-item__hint">{item.hint}</span>
                </span>
                {badgeValue ? <span className="nav-item__badge">{badgeValue}</span> : null}
              </button>
            );
          })}

          <span className="micro-label sidebar__nav-label sidebar__nav-label--spaced">Records</span>
          {PRIMARY_NAV.slice(3).map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={`nav-item ${view === item.id ? 'nav-item--active' : ''}`}
                onClick={() => navigate(item.id)}
                aria-current={view === item.id ? 'page' : undefined}
              >
                <Icon size={18} strokeWidth={1.8} />
                <span className="nav-item__copy">
                  <span className="nav-item__label">{item.label}</span>
                  <span className="nav-item__hint">{item.hint}</span>
                </span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar__network">
          <div className="sidebar__network-head">
            <span className="micro-label">Network health</span>
            <span className="mono-tiny">{summary ? `${summary.nodesOnline}/${summary.nodesTotal}` : '—'}</span>
          </div>
          <SystemRow
            label="LoRa gateway"
            value={gateway?.online ? 'Linked' : 'Offline'}
            tone={gateway?.online ? 'live' : 'alert'}
            detail={gateway?.lastSeen ? `Last packet ${formatRelative(gateway.lastSeen)}` : 'No packet received'}
          />
          <SystemRow
            label="Risk engine"
            value={severe ? 'Intervention advised' : 'Monitoring'}
            tone={severe ? 'alert' : 'live'}
            detail={severe ? severe.nodeName : 'All thresholds within tolerance'}
          />
          <SystemRow
            label="Simulation feed"
            value={snapshot?.meta?.simulation ? 'Streaming' : 'Manual ingest'}
            tone={snapshot?.meta?.simulation ? 'live' : 'quiet'}
            detail={peakNode ? `${peakNode.name} · ${riskLabel(peakNode.risk.level)}` : 'No sensor data'}
          />
        </div>

        <div className="sidebar__footer">
          <button
            className="sidebar__footer-line"
            style={{ background: 'transparent', border: 'none', color: 'inherit', width: '100%', textAlign: 'left', cursor: 'pointer', padding: 0 }}
            onClick={() => {
              alert('Authentication: District Disaster Management Authority (DDMA)\nRole: Authority access enabled\nSession: Authenticated via JWT\nAccess: Command console, overrides, evacuations permitted');
            }}
            title="View authentication details"
          >
            <ShieldCheck size={14} />
            <span>DDMA authenticated</span>
          </button>
          <div className="sidebar__footer-line sidebar__footer-line--muted">
            <Wifi size={13} />
            <span>v1.0 · Node 22+</span>
            <RadioTower size={13} />
          </div>
        </div>
      </aside>
      {open ? <button className="sidebar-scrim" onClick={onClose} aria-label="Close navigation" /> : null}
    </>
  );
}

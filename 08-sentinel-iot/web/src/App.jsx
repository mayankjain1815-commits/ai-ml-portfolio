import { useCallback, useEffect, useState } from 'react';
import { AlertTicker } from './components/AlertTicker.jsx';
import { NodeDetail } from './components/NodeDetail.jsx';
import { SentinelMark } from './components/Logo.jsx';
import { Sidebar } from './components/Sidebar.jsx';
import { ToastStack } from './components/ToastStack.jsx';
import { Topbar } from './components/Topbar.jsx';
import { Login } from './components/Login.jsx';
import { ProfileModal } from './components/ProfileModal.jsx';
import { api } from './lib/api.js';
import { alertTypeLabel } from './lib/format.js';
import { useSentinel } from './lib/useSentinel.js';
import { getToken, getUser } from './lib/auth.js';
import { AlertsView } from './views/AlertsView.jsx';
import { CommandView } from './views/CommandView.jsx';
import { IncidentsView } from './views/IncidentsView.jsx';
import { MapView } from './views/MapView.jsx';
import { Overview } from './views/Overview.jsx';

const VIEWS = ['overview', 'map', 'alerts', 'incidents', 'command'];

const VIEW_TITLES = {
  overview: 'Regional situation',
  map: 'Affected areas',
  alerts: 'Active alerts',
  incidents: 'Incident log',
  command: 'Command console',
};

function readViewFromHash() {
  const hash = window.location.hash.replace(/^#\/?/, '').trim();
  return VIEWS.includes(hash) ? hash : 'overview';
}

export function App() {
  const [view, setView] = useState(readViewFromHash);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [toasts, setToasts] = useState([]);
  const [busy, setBusy] = useState(false);
  const [authenticated, setAuthenticated] = useState(!!getToken());
  const [profileOpen, setProfileOpen] = useState(false);

  const pushToast = useCallback((message, tone = 'neutral', title) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    setToasts((current) => [...current.slice(-3), { id, message, tone, title }]);
  }, []);

  const dismissToast = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const handleAlert = useCallback(
    (alert) => {
      pushToast(
        alert.message,
        alert.severity === 'severe' ? 'warning' : 'neutral',
        `${alert.severity.toUpperCase()} · ${alertTypeLabel(alert.type)}`,
      );
    },
    [pushToast],
  );

  const { snapshot, connection, error, lastUpdated } = useSentinel({ onAlert: handleAlert });

  const navigate = useCallback((nextView) => {
    const target = VIEWS.includes(nextView) ? nextView : 'overview';
    setView(target);
    setSidebarOpen(false);
    if (window.location.hash !== `#/${target}`) {
      window.history.pushState(null, '', `#/${target}`);
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  useEffect(() => {
    const syncView = () => setView(readViewFromHash());
    window.addEventListener('hashchange', syncView);
    window.addEventListener('popstate', syncView);
    return () => {
      window.removeEventListener('hashchange', syncView);
      window.removeEventListener('popstate', syncView);
    };
  }, []);

  useEffect(() => {
    document.title = `${VIEW_TITLES[view] ?? 'Regional situation'} · SENTINEL`;
  }, [view]);

  const inspectNode = useCallback((nodeId) => {
    setSelectedNodeId(nodeId);
  }, []);

  const handleAcknowledge = useCallback(
    async (alertId) => {
      setBusy(true);
      try {
        await api.acknowledge(alertId, snapshot?.meta?.operator);
        pushToast('Warning acknowledged and written to the audit record', 'success', 'Acknowledgment recorded');
      } catch (actionError) {
        pushToast(actionError.message, 'error', 'Acknowledgment failed');
      } finally {
        setBusy(false);
      }
    },
    [pushToast, snapshot?.meta?.operator],
  );

  const handleAcknowledgeAll = useCallback(async () => {
    setBusy(true);
    try {
      const response = await api.acknowledgeAll(snapshot?.meta?.operator);
      pushToast(
        `${response.acknowledged} warning${response.acknowledged === 1 ? '' : 's'} acknowledged`,
        'success',
        'Queue cleared',
      );
    } catch (actionError) {
      pushToast(actionError.message, 'error', 'Bulk acknowledgment failed');
    } finally {
      setBusy(false);
    }
  }, [pushToast, snapshot?.meta?.operator]);

  const handleLogin = useCallback((user) => {
    setAuthenticated(true);
    pushToast(`Welcome, ${user?.username || 'Operator'}`, 'success', 'Authenticated');
  }, [pushToast]);

  const handleLogout = useCallback(() => {
    setAuthenticated(false);
    setProfileOpen(false);
    pushToast('Signed out successfully', 'neutral', 'Session ended');
  }, [pushToast]);

  if (!authenticated) {
    return <Login onLogin={handleLogin} />;
  }

  if (!snapshot) {
    return (
      <div className="boot-screen">
        <div className="boot-screen__mark">
          <SentinelMark size={72} />
        </div>
        {error ? (
          <>
            <span className="eyebrow">Telemetry unavailable</span>
            <h1>Command link interrupted</h1>
            <p>{error}</p>
            <button className="button button--primary" onClick={() => window.location.reload()}>
              Retry connection
            </button>
          </>
        ) : (
          <>
            <span className="eyebrow">SENTINEL · Disaster command</span>
            <h1>Establishing telemetry link</h1>
            <p>Negotiating WebSocket feed and loading the latest sector snapshot…</p>
            <div className="boot-screen__loader" aria-hidden="true">
              <span />
              <span />
              <span />
            </div>
          </>
        )}
      </div>
    );
  }

  const selectedNode = snapshot.nodes.find((node) => node.id === selectedNodeId) ?? null;
  const operator = snapshot.meta.operator;

  const renderView = () => {
    if (view === 'map') {
      return (
        <MapView
          snapshot={snapshot}
          onInspect={inspectNode}
          onNavigate={navigate}
          onAcknowledge={handleAcknowledge}
          onAcknowledgeAll={handleAcknowledgeAll}
          busy={busy}
        />
      );
    }

    if (view === 'alerts') {
      return (
        <AlertsView
          snapshot={snapshot}
          onAcknowledge={handleAcknowledge}
          onAcknowledgeAll={handleAcknowledgeAll}
          onInspect={inspectNode}
          onNavigate={navigate}
          busy={busy}
        />
      );
    }

    if (view === 'incidents') {
      return (
        <IncidentsView
          snapshot={snapshot}
          refreshToken={snapshot.incidents?.[0]?.id ?? 'none'}
          onToast={pushToast}
        />
      );
    }

    if (view === 'command') {
      return (
        <CommandView
          snapshot={snapshot}
          operator={operator}
          onInspect={inspectNode}
          onToast={pushToast}
        />
      );
    }

    return (
      <Overview
        snapshot={snapshot}
        onNavigate={navigate}
        onInspect={inspectNode}
        onAcknowledge={handleAcknowledge}
        onAcknowledgeAll={handleAcknowledgeAll}
        busy={busy}
        lastUpdated={lastUpdated}
      />
    );
  };

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to command content
      </a>

      <Sidebar
        view={view}
        onNavigate={navigate}
        snapshot={snapshot}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="app-body">
        <Topbar
          view={view}
          snapshot={snapshot}
          connection={connection}
          onMenu={() => setSidebarOpen(true)}
          onOpenAlerts={() => navigate('alerts')}
          onOpenProfile={() => setProfileOpen(true)}
        />

        <main className="app-content" id="main-content">
          {connection === 'offline' ? (
            <div className="connection-banner" role="status">
              <span className="status-dot" />
              <span>
                Telemetry link interrupted. The dashboard is showing the last confirmed snapshot while
                the client retries automatically.
              </span>
              <button className="button button--quiet button--tiny" onClick={() => window.location.reload()}>
                Reconnect now
              </button>
            </div>
          ) : null}

          <AlertTicker snapshot={snapshot} onNavigate={navigate} />

          {renderView()}

          <footer className="app-footer">
            <span>
              SENTINEL v{snapshot.meta.version} · {snapshot.meta.site.name} · {snapshot.meta.site.code}
            </span>
            <span>
              {snapshot.meta.simulation ? 'Simulation feed active' : 'Hardware ingestion only'} ·{' '}
              {connection === 'live' ? 'WebSocket live' : connection === 'polling' ? 'Polling fallback' : 'Offline'}
            </span>
            <span>
              {snapshot.meta.organization} · Duty authority {operator}
            </span>
          </footer>
        </main>
      </div>

      {selectedNode ? (
        <NodeDetail
          node={selectedNode}
          onClose={() => setSelectedNodeId(null)}
          onOpenCommand={() => navigate('command')}
        />
      ) : null}

      <ToastStack toasts={toasts} onDismiss={dismissToast} />
      <ProfileModal open={profileOpen} onClose={() => setProfileOpen(false)} onLogout={handleLogout} />
    </div>
  );
}

export default App;

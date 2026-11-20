import { ChevronRight, Radio, ShieldCheck, Siren, TriangleAlert } from 'lucide-react';
import { alertTypeLabel, formatRelative } from '../lib/format.js';

export function AlertTicker({ snapshot, onNavigate }) {
  const summary = snapshot?.summary;
  const alerts = snapshot?.alerts ?? [];
  const evacuation = snapshot?.system?.evacuation;
  const severe = alerts.find((alert) => alert.severity === 'severe' && alert.status !== 'resolved');
  const high = alerts.find((alert) => alert.severity === 'high' && alert.status !== 'resolved');

  if (evacuation?.active) {
    return (
      <div className="alert-ticker alert-ticker--evacuation" role="status" aria-live="polite">
        <div className="alert-ticker__tag">
          <Siren size={16} />
          EVACUATION
        </div>
        <div className="alert-ticker__body">
          <strong>Mandatory evacuation in effect.</strong>
          <span>{evacuation.reason}</span>
          <span className="alert-ticker__meta">
            {evacuation.targetName} · issued {formatRelative(evacuation.issuedAt)}
            {snapshot?.system?.siren?.enabled ? ' · public siren active' : ''}
          </span>
        </div>
        <button className="alert-ticker__action" onClick={() => onNavigate('command')}>
          Open command
          <ChevronRight size={15} />
        </button>
      </div>
    );
  }

  if (severe) {
    return (
      <div className="alert-ticker alert-ticker--severe" role="alert" aria-live="assertive">
        <div className="alert-ticker__tag">
          <TriangleAlert size={16} />
          SEVERE
        </div>
        <div className="alert-ticker__body">
          <strong>{severe.title}</strong>
          <span>{severe.message}</span>
          <span className="alert-ticker__meta">
            {alertTypeLabel(severe.type)} · {severe.nodeName} · {formatRelative(severe.createdAt)}
          </span>
        </div>
        <button className="alert-ticker__action" onClick={() => onNavigate('alerts')}>
          Review alert
          <ChevronRight size={15} />
        </button>
      </div>
    );
  }

  if (high) {
    return (
      <div className="alert-ticker alert-ticker--watch" role="status" aria-live="polite">
        <div className="alert-ticker__tag">
          <TriangleAlert size={15} />
          WATCH
        </div>
        <div className="alert-ticker__body">
          <strong>{high.title}</strong>
          <span className="alert-ticker__meta">
            {high.nodeName} · {formatRelative(high.createdAt)}
          </span>
        </div>
        <button className="alert-ticker__action" onClick={() => onNavigate('alerts')}>
          View {summary?.activeAlerts ?? 0} alerts
          <ChevronRight size={15} />
        </button>
      </div>
    );
  }

  return (
    <div className="alert-ticker alert-ticker--nominal" role="status" aria-live="polite">
      <div className="alert-ticker__tag">
        <ShieldCheck size={15} />
        NETWORK
      </div>
      <div className="alert-ticker__body">
        <strong>All monitored thresholds nominal.</strong>
        <span className="alert-ticker__meta">
          {summary?.nodesOnline ?? 0} node{summary?.nodesOnline === 1 ? '' : 's'} reporting · risk engine
          monitoring
        </span>
      </div>
      <div className="alert-ticker__signal">
        <Radio size={14} />
        LIVE
      </div>
    </div>
  );
}

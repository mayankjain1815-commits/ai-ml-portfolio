import { useMemo, useState } from 'react';
import {
  ArrowRight,
  BellRing,
  Check,
  CheckCheck,
  ChevronRight,
  CloudRain,
  Clock3,
  Mountain,
  Radio,
  ScrollText,
  Siren,
  ThermometerSun,
  TriangleAlert,
  Wind,
} from 'lucide-react';
import { Modal } from '../components/Modal.jsx';
import { RiskBadge } from '../components/RiskBadge.jsx';
import { StatCard } from '../components/StatCard.jsx';
import {
  alertTypeLabel,
  formatDateTime,
  formatRelative,
  formatTime,
  riskLabel,
  sourceLabel,
} from '../lib/format.js';

const ALERT_ICONS = {
  flood: CloudRain,
  landslide: Mountain,
  air_quality: Wind,
  heat: ThermometerSun,
  sos: Radio,
  evacuation: Siren,
};

const STATUS_FILTERS = [
  { id: 'all', label: 'All warnings' },
  { id: 'active', label: 'Unacknowledged' },
  { id: 'acknowledged', label: 'Acknowledged' },
];

const SEVERITY_FILTERS = ['all', 'severe', 'high', 'moderate', 'low'];

const ESCALATION_STEPS = [
  {
    step: '01',
    title: 'Acknowledge within 5 minutes',
    detail: 'Every warning must be claimed by a named duty officer so the audit trail shows ownership.',
  },
  {
    step: '02',
    title: 'Corroborate with a second signal',
    detail: 'Cross-check the contributing factors, node health and adjacent sensor nodes before escalating.',
  },
  {
    step: '03',
    title: 'Escalate life-safety threats',
    detail: 'Persistent severe flood or landslide risk triggers an evacuation order through the command console.',
  },
  {
    step: '04',
    title: 'Close the record',
    detail: 'Resolved hazards clear automatically once readings return below threshold for consecutive packets.',
  },
];

export function AlertsView({
  snapshot,
  onAcknowledge,
  onAcknowledgeAll,
  onInspect,
  onNavigate,
  busy,
}) {
  const [statusFilter, setStatusFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [selectedAlert, setSelectedAlert] = useState(null);

  const alerts = snapshot.alerts ?? [];
  const unacknowledged = alerts.filter((alert) => alert.status === 'active');
  const acknowledged = alerts.filter((alert) => alert.status === 'acknowledged');
  const severe = alerts.filter((alert) => alert.severity === 'severe');
  const high = alerts.filter((alert) => alert.severity === 'high');

  const filtered = useMemo(
    () =>
      alerts.filter((alert) => {
        if (statusFilter !== 'all' && alert.status !== statusFilter) return false;
        if (severityFilter !== 'all' && alert.severity !== severityFilter) return false;
        return true;
      }),
    [alerts, statusFilter, severityFilter],
  );

  const sourceCounts = useMemo(() => {
    const counts = new Map();
    alerts.forEach((alert) => {
      const key = sourceLabel(alert.source);
      counts.set(key, (counts.get(key) ?? 0) + 1);
    });
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [alerts]);

  const selected = selectedAlert ? alerts.find((alert) => alert.id === selectedAlert.id) : null;

  return (
    <div className="view-stack alerts-view">
      <div className="view-lead">
        <div>
          <span className="eyebrow">Emergency communications</span>
          <h2>Warning stream</h2>
          <p>
            {unacknowledged.length} unacknowledged warning{unacknowledged.length === 1 ? '' : 's'} ·{' '}
            {severe.length} severe · {acknowledged.length} acknowledged by duty officers
          </p>
        </div>
        <div className="view-lead__meta">
          <span className="sync-stamp">
            <Clock3 size={12} />
            Live from risk engine
          </span>
          {unacknowledged.length ? (
            <button className="button button--primary button--small" onClick={onAcknowledgeAll} disabled={busy}>
              <CheckCheck size={14} />
              Acknowledge all
            </button>
          ) : null}
        </div>
      </div>

      <div className="stat-grid stat-grid--four">
        <StatCard
          label="Severe warnings"
          value={severe.length}
          detail="Life-safety intervention threshold"
          icon={Siren}
          tone={severe.length ? 'severe' : 'default'}
        />
        <StatCard
          label="High warnings"
          value={high.length}
          detail="Escalation monitoring required"
          icon={TriangleAlert}
          tone={high.length ? 'high' : 'default'}
        />
        <StatCard
          label="Awaiting acknowledgment"
          value={unacknowledged.length}
          detail={`${acknowledged.length} already claimed`}
          icon={BellRing}
          tone={unacknowledged.length ? 'high' : 'default'}
        />
        <StatCard
          label="Warning queue"
          value={alerts.length}
          detail="Active and acknowledged records"
          icon={ScrollText}
          tone="default"
        />
      </div>

      <div className="alerts-grid">
        <section className="panel alerts-stream">
          <header className="panel__head">
            <div>
              <span className="eyebrow">Automated and operator warnings</span>
              <h2>
                Alert queue
                <span className="panel__count">{filtered.length}</span>
              </h2>
            </div>
            <span className="live-label">
              <span className="status-dot status-dot--pulse" />
              Streaming
            </span>
          </header>

          <div className="alert-filters" role="group" aria-label="Alert filters">
            <div className="alert-filters__group">
              {STATUS_FILTERS.map((option) => (
                <button
                  key={option.id}
                  className={`filter-chip ${statusFilter === option.id ? 'filter-chip--active' : ''}`}
                  onClick={() => setStatusFilter(option.id)}
                  aria-pressed={statusFilter === option.id}
                >
                  {option.label}
                </button>
              ))}
            </div>
            <label className="select-field select-field--inline">
              <span>Severity</span>
              <select value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)}>
                {SEVERITY_FILTERS.map((level) => (
                  <option key={level} value={level}>
                    {level === 'all' ? 'All levels' : riskLabel(level)}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {filtered.length === 0 ? (
            <div className="empty-state">
              <span className="empty-state__icon">
                <Check size={20} />
              </span>
              <div>
                <strong>No warnings match this view</strong>
                <p>Change the status or severity filter to inspect the rest of the active queue.</p>
                <button
                  className="button button--quiet button--tiny"
                  onClick={() => {
                    setStatusFilter('all');
                    setSeverityFilter('all');
                  }}
                >
                  Reset filters
                </button>
              </div>
            </div>
          ) : (
            <div className="alert-feed__list alert-list">
              {filtered.map((alert) => {
                const Icon = ALERT_ICONS[alert.type] ?? TriangleAlert;
                return (
                  <article className={`alert-card alert-card--${alert.severity}`} key={alert.id}>
                    <div className="alert-card__stripe" />
                    <div className="alert-card__top">
                      <span className="alert-card__icon">
                        <Icon size={15} />
                      </span>
                      <div className="alert-card__meta">
                        <span className={`alert-card__severity alert-card__severity--${alert.severity}`}>
                          {alert.severity}
                        </span>
                        <span>{alertTypeLabel(alert.type)}</span>
                        <span className="alert-card__dot">·</span>
                        <span>{formatRelative(alert.createdAt)}</span>
                      </div>
                      <span className="alert-card__time">{formatTime(alert.createdAt)}</span>
                    </div>
                    <h3>{alert.title}</h3>
                    <p className="alert-card__message">{alert.message}</p>
                    <div className="alert-card__footer">
                      <span className="alert-card__node">{alert.nodeName ?? 'Regional command'}</span>
                      <span className="alert-card__source">{sourceLabel(alert.source)}</span>
                      {alert.status === 'active' ? (
                        <button
                          className="alert-card__ack"
                          onClick={() => onAcknowledge(alert.id)}
                          disabled={busy}
                        >
                          <Check size={13} />
                          Acknowledge
                        </button>
                      ) : (
                        <span className="alert-card__acknowledged">
                          <Check size={12} />
                          Acknowledged
                          {alert.acknowledgedBy ? ` · ${alert.acknowledgedBy.replace('Duty Officer ', '')}` : ''}
                        </span>
                      )}
                      <button
                        className="alert-card__open"
                        onClick={() => setSelectedAlert(alert)}
                        aria-label={`Open warning ${alert.id}`}
                      >
                        Record
                        <ChevronRight size={13} />
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <aside className="alerts-rail">
          <section className="panel alert-protocol">
            <header className="panel__head">
              <div>
                <span className="eyebrow">Standard operating procedure</span>
                <h2>Escalation protocol</h2>
              </div>
            </header>
            <ol className="protocol-list">
              {ESCALATION_STEPS.map((item) => (
                <li key={item.step}>
                  <span className="protocol-list__step">{item.step}</span>
                  <div>
                    <strong>{item.title}</strong>
                    <p>{item.detail}</p>
                  </div>
                </li>
              ))}
            </ol>
          </section>

          <section className="panel alert-sources">
            <header className="panel__head">
              <div>
                <span className="eyebrow">Signal provenance</span>
                <h2>Alert sources</h2>
              </div>
            </header>
            <div className="source-list">
              {sourceCounts.map(([label, count]) => (
                <div className="source-row" key={label}>
                  <span>{label}</span>
                  <span className="source-row__track">
                    <span style={{ width: `${Math.max(8, (count / alerts.length) * 100)}%` }} />
                  </span>
                  <strong>{count}</strong>
                </div>
              ))}
            </div>
          </section>

          <section className="panel alert-shortcuts">
            <div>
              <span className="eyebrow">Next actions</span>
              <h2>Command routing</h2>
            </div>
            <button className="button button--primary" onClick={() => onNavigate('command')}>
              <Siren size={15} />
              Open command console
              <ArrowRight size={14} />
            </button>
            <button className="button button--quiet" onClick={() => onNavigate('incidents')}>
              <ScrollText size={15} />
              Review incident log
            </button>
          </section>
        </aside>
      </div>

      {selected ? (
        <Modal
          title={selected.title}
          eyebrow={`${alertTypeLabel(selected.type)} · ${formatDateTime(selected.createdAt)}`}
          onClose={() => setSelectedAlert(null)}
          size="medium"
          footer={
            <>
              {onInspect && selected.nodeId ? (
                <button
                  className="button button--quiet"
                  onClick={() => {
                    setSelectedAlert(null);
                    onInspect(selected.nodeId);
                  }}
                >
                  Node diagnostics
                </button>
              ) : null}
              {selected.status === 'active' ? (
                <button
                  className="button button--primary"
                  onClick={() => {
                    onAcknowledge(selected.id);
                    setSelectedAlert(null);
                  }}
                  disabled={busy}
                >
                  <Check size={15} />
                  Acknowledge warning
                </button>
              ) : (
                <button className="button button--primary" onClick={() => setSelectedAlert(null)}>
                  Close record
                </button>
              )}
            </>
          }
        >
          <div className="incident-detail">
            <div className="incident-detail__meta">
              <div>
                <span className="micro-label">Severity</span>
                <RiskBadge level={selected.severity} />
              </div>
              <div>
                <span className="micro-label">Status</span>
                <span className={`status-pill status-pill--${selected.status}`}>{selected.status}</span>
              </div>
              <div>
                <span className="micro-label">Node</span>
                <span className="incident-detail__value">{selected.nodeName ?? 'Regional command'}</span>
              </div>
              <div>
                <span className="micro-label">Source</span>
                <span className="incident-detail__value">{sourceLabel(selected.source)}</span>
              </div>
            </div>
            <div className="incident-detail__section">
              <span className="micro-label">Warning detail</span>
              <p>{selected.message}</p>
            </div>
            <div className="incident-detail__meta incident-detail__meta--times">
              <div>
                <span className="micro-label">Raised</span>
                <span className="incident-detail__value">{formatDateTime(selected.createdAt)}</span>
              </div>
              <div>
                <span className="micro-label">Updated</span>
                <span className="incident-detail__value">{formatDateTime(selected.updatedAt)}</span>
              </div>
              <div>
                <span className="micro-label">Acknowledged by</span>
                <span className="incident-detail__value">{selected.acknowledgedBy ?? 'Not acknowledged'}</span>
              </div>
            </div>
            {selected.metadata && Object.keys(selected.metadata).length ? (
              <div className="incident-detail__section">
                <span className="micro-label">Risk evidence</span>
                <pre>{JSON.stringify(selected.metadata, null, 2)}</pre>
              </div>
            ) : null}
          </div>
        </Modal>
      ) : null}
    </div>
  );
}

import { ArrowRight, FileText } from 'lucide-react';
import { formatDateTime, formatRelative, incidentTypeLabel } from '../lib/format.js';
import { RiskBadge } from './RiskBadge.jsx';

export function RecentIncidents({ incidents = [], onOpenLog }) {
  return (
    <section className="panel recent-incidents">
      <header className="panel__head">
        <div>
          <span className="eyebrow">Field record</span>
          <h2>Latest incidents</h2>
        </div>
        <button className="button button--quiet button--small" onClick={onOpenLog}>
          Open incident log
          <ArrowRight size={14} />
        </button>
      </header>
      <div className="recent-incidents__table" role="table" aria-label="Latest incidents">
        <div className="recent-incidents__head" role="row">
          <span>Time</span>
          <span>Event</span>
          <span>Node / area</span>
          <span>Type</span>
          <span>Severity</span>
          <span>Status</span>
        </div>
        {incidents.length === 0 ? (
          <div className="empty-state empty-state--compact">
            <span className="empty-state__icon">
              <FileText size={19} />
            </span>
            <div>
              <strong>No field events yet</strong>
              <p>Incoming sensor warnings will be written to this log automatically.</p>
            </div>
          </div>
        ) : (
          incidents.map((incident) => (
            <div className="recent-incidents__row" role="row" key={incident.id}>
              <span className="recent-incidents__time">
                <strong>{formatDateTime(incident.createdAt).split(', ')[1] ?? formatDateTime(incident.createdAt)}</strong>
                <small>{formatRelative(incident.createdAt)}</small>
              </span>
              <span className="recent-incidents__event">
                <strong>{incident.title}</strong>
                <small>{incident.detail}</small>
              </span>
              <span>{incident.nodeName ?? 'Regional'}</span>
              <span className="type-pill">{incidentTypeLabel(incident.type)}</span>
              <span>
                <RiskBadge level={incident.severity} compact />
              </span>
              <span className={`status-pill status-pill--${incident.status}`}>{incident.status}</span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

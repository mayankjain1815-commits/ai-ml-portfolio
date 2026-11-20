import {
  Check,
  CheckCheck,
  ChevronRight,
  CloudRain,
  Mountain,
  Radio,
  Siren,
  ThermometerSun,
  TriangleAlert,
  Wind,
} from 'lucide-react';
import { RiskBadge } from './RiskBadge.jsx';
import { alertTypeLabel, formatRelative, formatTime, sourceLabel } from '../lib/format.js';

const ALERT_ICONS = {
  flood: CloudRain,
  landslide: Mountain,
  air_quality: Wind,
  heat: ThermometerSun,
  sos: Radio,
  evacuation: Siren,
};

export function AlertFeed({
  alerts = [],
  compact = false,
  onAcknowledge,
  onAcknowledgeAll,
  onOpen,
  busy = false,
}) {
  const activeAlerts = alerts.filter((alert) => alert.status !== 'resolved');
  const unacknowledged = activeAlerts.filter((alert) => alert.status === 'active');
  const visible = compact ? activeAlerts.slice(0, 4) : activeAlerts;

  return (
    <section className={`panel alert-feed ${compact ? 'alert-feed--compact' : ''}`}>
      <header className="panel__head">
        <div>
          <span className="eyebrow">Emergency comms</span>
          <h2>
            Active alerts
            <span className="panel__count">{activeAlerts.length}</span>
          </h2>
        </div>
        {onAcknowledgeAll && unacknowledged.length > 0 ? (
          <button className="button button--quiet button--small" onClick={onAcknowledgeAll} disabled={busy}>
            <CheckCheck size={14} />
            Acknowledge all
          </button>
        ) : null}
      </header>

      {activeAlerts.length === 0 ? (
        <div className="empty-state empty-state--compact">
          <span className="empty-state__icon">
            <Check size={20} />
          </span>
          <div>
            <strong>No active warnings</strong>
            <p>All sensor nodes are reporting below alert thresholds.</p>
          </div>
        </div>
      ) : (
        <div className="alert-feed__list">
          {visible.map((alert) => {
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
                  {alert.status === 'active' && onAcknowledge ? (
                    <button
                      className="alert-card__ack"
                      onClick={() => onAcknowledge(alert.id)}
                      disabled={busy}
                    >
                      <Check size={13} />
                      Acknowledge
                    </button>
                  ) : null}
                  {alert.status === 'acknowledged' ? (
                    <span className="alert-card__acknowledged">
                      <Check size={12} />
                      Acknowledged
                      {alert.acknowledgedBy ? ` · ${alert.acknowledgedBy.replace('Duty Officer ', '')}` : ''}
                    </span>
                  ) : null}
                </div>
              </article>
            );
          })}
          {compact && activeAlerts.length > visible.length ? (
            <button className="alert-feed__more" onClick={() => onOpen?.('alerts')}>
              View all {activeAlerts.length} warnings
              <ChevronRight size={14} />
            </button>
          ) : null}
        </div>
      )}

      {!compact && activeAlerts.length > 0 ? (
        <footer className="panel__foot alert-feed__foot">
          <span>
            <span className="status-dot status-dot--pulse" />
            Warning stream auto-refreshes
          </span>
          <RiskBadge level={activeAlerts.some((alert) => alert.severity === 'severe') ? 'severe' : 'high'}>
            {unacknowledged.length} unacknowledged
          </RiskBadge>
        </footer>
      ) : null}
    </section>
  );
}

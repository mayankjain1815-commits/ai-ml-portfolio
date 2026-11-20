import { Activity, BellRing, FileClock, RadioTower } from 'lucide-react';
import { IncidentTable } from '../components/IncidentTable.jsx';
import { StatCard } from '../components/StatCard.jsx';
import { formatNumber } from '../lib/format.js';

export function IncidentsView({ snapshot, refreshToken, onToast }) {
  const stats = snapshot.incidentStats ?? {};
  const total24h = Object.values(stats).reduce((sum, value) => sum + Number(value || 0), 0);
  const severe24h = Number(stats.severe || 0);
  const high24h = Number(stats.high || 0);
  const { summary, gateway } = snapshot;

  return (
    <div className="view-stack incidents-view">
      <div className="view-lead">
        <div>
          <span className="eyebrow">Operational archive</span>
          <h2>Incident and audit record</h2>
          <p>
            Every warning, sensor transition and operator command is retained in the sector audit trail.
            Search, filter and export the last 24 hours of activity.
          </p>
        </div>
        <div className="view-lead__meta">
          <span className="sync-stamp">
            <FileClock size={12} />
            Retained 30 days
          </span>
        </div>
      </div>

      <div className="stat-grid stat-grid--four">
        <StatCard
          label="Events · last 24h"
          value={formatNumber(total24h, { maximumFractionDigits: 0 })}
          detail="Sensor, command and authority records"
          icon={Activity}
          tone="default"
        />
        <StatCard
          label="Severe events"
          value={severe24h}
          detail={`${high24h} high-severity events logged`}
          icon={BellRing}
          tone={severe24h ? 'severe' : 'default'}
        />
        <StatCard
          label="Open warnings"
          value={summary.activeAlerts}
          detail={`${summary.unacknowledgedAlerts} awaiting acknowledgment`}
          icon={BellRing}
          tone={summary.activeAlerts ? 'high' : 'default'}
        />
        <StatCard
          label="Gateway packets"
          value={formatNumber(gateway?.packets, { maximumFractionDigits: 0 })}
          detail={gateway?.online ? `${gateway.id} · link healthy` : 'Gateway link offline'}
          icon={RadioTower}
          tone={gateway?.online ? 'default' : 'high'}
        />
      </div>

      <IncidentTable refreshToken={refreshToken} onToast={onToast} />

      <p className="record-footnote">
        Records are immutable once written. Acknowledging an alert adds a linked acknowledgement event;
        it does not alter the original warning. Census population figures remain fixed at commissioning.
      </p>
    </div>
  );
}

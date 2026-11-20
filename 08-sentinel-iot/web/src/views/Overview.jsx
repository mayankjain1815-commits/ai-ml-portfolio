import {
  Activity,
  ArrowRight,
  BellRing,
  RadioTower,
  RefreshCw,
  Users,
} from 'lucide-react';
import { StatCard } from '../components/StatCard.jsx';
import { SensorCard } from '../components/SensorCard.jsx';
import { InteractiveMap } from '../components/InteractiveMap.jsx';
import { RegionalRiskPanel } from '../components/RegionalRiskPanel.jsx';
import { AlertFeed } from '../components/AlertFeed.jsx';
import { RecentIncidents } from '../components/RecentIncidents.jsx';
import { EvacuationPanel } from '../components/EvacuationPanel.jsx';
import { formatNumber, formatRelative } from '../lib/format.js';

export function Overview({
  snapshot,
  onNavigate,
  onInspect,
  onAcknowledge,
  onAcknowledgeAll,
  busy,
  lastUpdated,
}) {
  const { summary, nodes, incidents } = snapshot;

  return (
    <div className="view-stack overview-view">
      <div className="view-lead">
        <div>
          <span className="eyebrow">Live operational picture</span>
          <h2>{snapshot.meta.site.name} sensor network</h2>
          <p>
            {summary.nodesOnline} of {summary.nodesTotal} remote nodes reporting · evacuation posture{' '}
            <strong>{summary.evacuationActive ? 'ACTIVE' : 'normal'}</strong>
          </p>
        </div>
        <div className="view-lead__meta">
          <span className="sync-stamp">
            <RefreshCw size={12} />
            Synced {formatRelative(lastUpdated ?? snapshot.meta.generatedAt)}
          </span>
          <button className="button button--quiet button--small" onClick={() => onNavigate('map')}>
            Full geospatial view
            <ArrowRight size={14} />
          </button>
        </div>
      </div>

      <div className="stat-grid">
        <StatCard
          label="Peak risk index"
          value={Math.round(summary.peakRisk)}
          suffix="/ 100"
          detail={`${summary.peakNode?.name ?? 'No node'} · ${summary.peakRiskLevel} condition`}
          icon={Activity}
          tone={summary.peakRiskLevel}
        >
          <div className="mini-distribution" aria-hidden="true">
            {['low', 'moderate', 'high', 'severe'].map((level) => (
              <span
                className={`mini-distribution__segment mini-distribution__segment--${level}`}
                key={level}
                style={{
                  flex: summary.riskDistribution[level] || 0,
                  opacity: summary.riskDistribution[level] ? 1 : 0.18,
                }}
              />
            ))}
          </div>
        </StatCard>

        <StatCard
          label="Nodes reporting"
          value={`${summary.nodesOnline}/${summary.nodesTotal}`}
          detail={`${summary.networkUptime}% network availability · LoRa uplink`}
          icon={RadioTower}
          tone="default"
        >
          <div className="node-dots">
            {nodes.map((node) => (
              <span className={`node-dot node-dot--${node.risk.level}`} key={node.id} title={node.name}>
                <span />
              </span>
            ))}
          </div>
        </StatCard>

        <StatCard
          label="Active warnings"
          value={summary.activeAlerts}
          suffix={summary.activeAlerts === 1 ? 'alert' : 'alerts'}
          detail={`${summary.criticalAlerts} severe · ${summary.unacknowledgedAlerts} awaiting acknowledgment`}
          icon={BellRing}
          tone={summary.criticalAlerts ? 'severe' : summary.activeAlerts ? 'high' : 'default'}
          onClick={() => onNavigate?.('alerts')}
          clickable
        >
          <div className="alert-mini-bars" aria-hidden="true">
            {Array.from({ length: 12 }).map((_, index) => (
              <span
                key={index}
                className={index < summary.unacknowledgedAlerts ? 'is-active' : ''}
                style={{ height: `${index < summary.unacknowledgedAlerts ? 34 + index * 3 : 12}%` }}
              />
            ))}
          </div>
        </StatCard>

        <StatCard
          label="Population exposed"
          value={formatNumber(summary.affectedPopulation, { maximumFractionDigits: 0 })}
          detail={`Residents inside ${summary.riskDistribution.high + summary.riskDistribution.severe} high-risk sectors`}
          icon={Users}
          tone={summary.affectedPopulation > 0 ? 'high' : 'default'}
        >
          <span className="population-caption">
            <span className="population-caption__dot" />
            Live exposure estimate
          </span>
        </StatCard>
      </div>

      <div className="overview-grid">
        <div className="overview-main">
          <section className="network-block">
            <header className="section-heading">
              <div>
                <span className="eyebrow">Field sensor network</span>
                <h2>Node telemetry</h2>
              </div>
              <span className="section-heading__meta">
                {summary.nodesOnline} online · packet interval 4 s
              </span>
            </header>
            <div className="sensor-grid">
              {nodes.map((node) => (
                <SensorCard key={node.id} node={node} onInspect={onInspect} />
              ))}
            </div>
          </section>

          <section className="panel map-panel">
            <header className="panel__head">
              <div>
                <span className="eyebrow">Geospatial intelligence</span>
                <h2>Affected areas</h2>
              </div>
              <div className="map-panel__actions">
                <span className="map-panel__hint">GPS-located · risk envelopes</span>
                <button className="button button--quiet button--small" onClick={() => onNavigate('map')}>
                  Expand map
                  <ArrowRight size={14} />
                </button>
              </div>
            </header>
            <InteractiveMap nodes={nodes} />
          </section>
        </div>

        <aside className="overview-rail">
          <EvacuationPanel />
          <RegionalRiskPanel snapshot={snapshot} />
          <AlertFeed
            alerts={snapshot.alerts}
            compact
            onAcknowledge={onAcknowledge}
            onAcknowledgeAll={onAcknowledgeAll}
            onOpen={onNavigate}
            busy={busy}
          />
        </aside>
      </div>

      <RecentIncidents incidents={incidents} onOpenLog={() => onNavigate('incidents')} />
    </div>
  );
}

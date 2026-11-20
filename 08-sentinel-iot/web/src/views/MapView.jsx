import { useEffect, useState } from 'react';
import {
  ArrowRight,
  BatteryMedium,
  CloudRain,
  LocateFixed,
  Mountain,
  Radio,
  Thermometer,
  Waves,
} from 'lucide-react';
import { AlertFeed } from '../components/AlertFeed.jsx';
import { InteractiveMap } from '../components/InteractiveMap.jsx';
import { RiskBadge } from '../components/RiskBadge.jsx';
import { RiskGauge } from '../components/RiskGauge.jsx';
import {
  formatBattery,
  formatCoordinate,
  formatNumber,
  formatRelative,
  riskLabel,
} from '../lib/format.js';

export function MapView({
  snapshot,
  onInspect,
  onNavigate,
  onAcknowledge,
  onAcknowledgeAll,
  busy,
}) {
  const { nodes, summary } = snapshot;
  const [selectedNodeId, setSelectedNodeId] = useState(summary.peakNode?.id ?? nodes[0]?.id);
  const selectedNode = nodes.find((node) => node.id === selectedNodeId) ?? nodes[0];

  useEffect(() => {
    if (!nodes.some((node) => node.id === selectedNodeId) && nodes[0]) {
      setSelectedNodeId(nodes[0].id);
    }
  }, [nodes, selectedNodeId]);

  const factorMax = Math.max(
    1,
    ...(selectedNode?.risk.topFactors ?? []).map((factor) => Number(factor.points) || 0),
  );

  return (
    <div className="view-stack map-view">
      <div className="view-lead">
        <div>
          <span className="eyebrow">GY-NEO6MV2 GPS fixes</span>
          <h2>{snapshot?.meta?.site?.name ?? 'Nashik Basin'} impact envelope</h2>
          <p>
            Risk radii are projected from live sensor coordinates and the composite hazard index. Click a
            node to inspect diagnostics.
          </p>
        </div>
        <div className="map-view__summary">
          <div>
            <span className="micro-label">Peak node</span>
            <strong>{summary.peakNode?.name}</strong>
          </div>
          <RiskBadge level={summary.peakRiskLevel}>{riskLabel(summary.peakRiskLevel)}</RiskBadge>
          <div>
            <span className="micro-label">Exposed</span>
            <strong>{formatNumber(summary.affectedPopulation, { maximumFractionDigits: 0 })}</strong>
          </div>
        </div>
      </div>

      <div className="map-view__grid">
        <section className="panel map-view__map-panel">
          <header className="panel__head">
            <div>
              <span className="eyebrow">Affected areas map</span>
              <h2>Live threat geometry</h2>
            </div>
            <div className="map-view__node-switcher">
              {nodes.map((node) => (
                <button
                  key={node.id}
                  className={`map-switcher ${selectedNode.id === node.id ? 'map-switcher--active' : ''}`}
                  onClick={() => setSelectedNodeId(node.id)}
                >
                  <span className={`map-switcher__dot map-switcher__dot--${node.risk.level}`} />
                  {node.name}
                </button>
              ))}
            </div>
          </header>
          <InteractiveMap
            nodes={nodes}
            selectedNodeId={selectedNodeId}
            onSelectNode={setSelectedNodeId}
            className="map-view__map"
            center={snapshot?.meta?.site?.center}
            bounds={snapshot?.meta?.site?.bounds}
          />
          <footer className="map-view__map-footer">
            <span>
              <span className="status-dot status-dot--pulse" /> GPS telemetry live from three field nodes
            </span>
            <span>Impact radius scales with composite risk index</span>
          </footer>
        </section>

        <aside className="map-view__side">
          {selectedNode ? (
            <section className="panel map-node-card">
              <header className="map-node-card__head">
                <div>
                  <span className="eyebrow">Selected node</span>
                  <h2>{selectedNode.name}</h2>
                  <span className="map-node-card__id">{selectedNode.id}</span>
                </div>
                <RiskBadge level={selectedNode.risk.level} />
              </header>

              <div className="map-node-card__gauge">
                <RiskGauge
                  score={selectedNode.risk.score}
                  level={selectedNode.risk.level}
                  size="small"
                  label="Composite index"
                />
                <div className="map-node-card__gauge-copy">
                  <span className="micro-label">Risk headline</span>
                  <strong>{selectedNode.risk.headline}</strong>
                  <span>{selectedNode.risk.advisory}</span>
                </div>
              </div>

              <div className="map-node-card__coordinates">
                <LocateFixed size={13} />
                <span>{formatCoordinate(selectedNode.lat, 'lat')}</span>
                <span>{formatCoordinate(selectedNode.lon, 'lon')}</span>
              </div>

              <div className="map-node-card__metrics">
                <div>
                  <span>
                    <Waves size={13} /> Water depth
                  </span>
                  <strong>{formatNumber(selectedNode.latest.waterLevel)} cm</strong>
                </div>
                <div>
                  <span>
                    <CloudRain size={13} /> Rainfall
                  </span>
                  <strong>{formatNumber(selectedNode.latest.rain)} mm/h</strong>
                </div>
                <div>
                  <span>
                    <Thermometer size={13} /> Temperature
                  </span>
                  <strong>{formatNumber(selectedNode.latest.temp)}°C</strong>
                </div>
                <div>
                  <span>
                    <Mountain size={13} /> Vibration
                  </span>
                  <strong>{selectedNode.latest.vibration ? 'Movement' : 'Stable'}</strong>
                </div>
              </div>

              <div className="map-node-card__section">
                <span className="micro-label">Primary contributors</span>
                {(selectedNode.risk.topFactors ?? []).slice(0, 3).map((factor) => (
                  <div className="mini-factor" key={`${factor.label}-${factor.value}`}>
                    <span>{factor.label}</span>
                    <div>
                      <span style={{ width: `${Math.min(100, (factor.points / factorMax) * 100)}%` }} />
                    </div>
                    <strong>{factor.value}</strong>
                  </div>
                ))}
              </div>

              <div className="map-node-card__health">
                <span>
                  <BatteryMedium size={13} /> {formatBattery(selectedNode.latest.battery)} · {selectedNode.health.batteryPercent}%
                </span>
                <span>
                  <Radio size={13} /> {selectedNode.latest.rssi} dBm
                </span>
                <span>Last packet {formatRelative(selectedNode.health.lastSeen)}</span>
              </div>

              <div className="map-node-card__actions">
                <button className="button button--quiet" onClick={() => onInspect(selectedNode.id)}>
                  Full diagnostics
                </button>
                <button className="button button--primary" onClick={() => onNavigate('command')}>
                  Command actions
                  <ArrowRight size={14} />
                </button>
              </div>
            </section>
          ) : null}

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
    </div>
  );
}

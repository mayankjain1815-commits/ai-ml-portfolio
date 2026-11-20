import { BatteryMedium, Cable, RadioTower, Signal, Wifi } from 'lucide-react';
import { RiskBadge } from './RiskBadge.jsx';
import {
  formatAge,
  formatBattery,
  formatNumber,
  formatRelative,
} from '../lib/format.js';

export function NodeHealth({ nodes = [], gateway, onInspect }) {
  return (
    <section className="panel node-health">
      <header className="panel__head">
        <div>
          <span className="eyebrow">Network operations</span>
          <h2>Node health</h2>
        </div>
        <span className={`link-badge link-badge--${gateway?.online ? 'nominal' : 'weak'}`}>
          <RadioTower size={13} />
          {gateway?.online ? 'Gateway linked' : 'Gateway offline'}
        </span>
      </header>

      <div className="node-health__gateway">
        <div className="node-health__gateway-icon">
          <Wifi size={18} />
        </div>
        <div>
          <span className="micro-label">Central gateway</span>
          <strong>{gateway?.id ?? 'GW-NSK-01'}</strong>
          <span className="node-health__gateway-detail">
            <Cable size={12} />
            {gateway?.firmware ?? 'sentinel-gw 1.4.2'} · {formatNumber(gateway?.packets, { maximumFractionDigits: 0 })} packets
          </span>
        </div>
        <div className="node-health__gateway-meta">
          <span className={`status-pill ${gateway?.online ? 'status-pill--monitoring' : 'status-pill--open'}`}>
            {gateway?.online ? 'Online' : 'No link'}
          </span>
          <span>{gateway?.lastSeen ? formatRelative(gateway.lastSeen) : 'No telemetry'}</span>
        </div>
      </div>

      <div className="node-health__table">
        <div className="node-health__row node-health__row--head">
          <span>Node</span>
          <span>Battery</span>
          <span>Link</span>
          <span>Packets</span>
          <span>Last seen</span>
          <span>Risk</span>
          <span />
        </div>
        {nodes.map((node) => (
          <div className="node-health__row" key={node.id}>
            <span className="node-health__node">
              <strong>{node.name}</strong>
              <small>{node.id}</small>
            </span>
            <span className="node-health__battery">
              <span className="node-health__battery-value">
                <BatteryMedium size={14} />
                {node.health.batteryPercent}%
              </span>
              <span className="node-health__battery-track">
                <span style={{ width: `${node.health.batteryPercent}%` }} />
              </span>
              <small>{formatBattery(node.latest.battery)}</small>
            </span>
            <span className="node-health__link">
              <Signal size={13} />
              {node.latest.rssi} dBm
              <small>SNR {formatNumber(node.latest.snr)}</small>
            </span>
            <span className="mono-tiny">{formatNumber(node.health.packetCount, { maximumFractionDigits: 0 })}</span>
            <span className="node-health__age">{formatAge(node.health.ageSeconds)}</span>
            <span>
              <RiskBadge level={node.risk.level} compact />
            </span>
            <button className="button button--quiet button--tiny" onClick={() => onInspect(node.id)}>
              Detail
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}

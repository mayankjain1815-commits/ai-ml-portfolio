import { useEffect, useState } from 'react';
import {
  BatteryMedium,
  Cpu,
  Gauge,
  LocateFixed,
  Radio,
  Satellite,
  ShieldCheck,
  Signal,
} from 'lucide-react';
import { api } from '../lib/api.js';
import {
  formatBattery,
  formatCoordinate,
  formatNumber,
  formatRelative,
  riskLabel,
} from '../lib/format.js';
import { Modal } from './Modal.jsx';
import { RiskBadge } from './RiskBadge.jsx';
import { RiskGauge } from './RiskGauge.jsx';

function HistoryChart({ title, unit, values = [], times = [], accent = 'marigold' }) {
  const numeric = values.filter((value) => Number.isFinite(Number(value)));
  if (numeric.length < 2) {
    return (
      <div className="history-chart history-chart--empty">
        <span className="micro-label">{title}</span>
        <span>Insufficient packets</span>
      </div>
    );
  }

  const width = 330;
  const height = 78;
  const min = Math.min(...numeric);
  const max = Math.max(...numeric);
  const range = max - min || 1;
  const points = numeric.map((value, index) => {
    const x = 4 + (index / (numeric.length - 1)) * (width - 8);
    const y = height - 8 - ((Number(value) - min) / range) * (height - 18);
    return [Number(x.toFixed(1)), Number(y.toFixed(1))];
  });
  const line = points.map(([x, y], index) => `${index === 0 ? 'M' : 'L'}${x},${y}`).join(' ');
  const area = `${line} L${points.at(-1)[0]},${height} L${points[0][0]},${height} Z`;
  const latest = numeric.at(-1);

  return (
    <div className={`history-chart history-chart--${accent}`}>
      <div className="history-chart__head">
        <span className="micro-label">{title}</span>
        <strong>
          {formatNumber(latest)} <small>{unit}</small>
        </strong>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" aria-hidden="true">
        <line className="history-chart__grid" x1="0" y1="18" x2={width} y2="18" />
        <line className="history-chart__grid" x1="0" y1="45" x2={width} y2="45" />
        <line className="history-chart__grid" x1="0" y1={height - 8} x2={width} y2={height - 8} />
        <path className="history-chart__area" d={area} />
        <path className="history-chart__line" d={line} vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="history-chart__axis">
        <span>{times[0] ? new Date(times[0]).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}</span>
        <span>{times.at(-1) ? new Date(times.at(-1)).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}</span>
      </div>
    </div>
  );
}

const SENSOR_SUITE = [
  ['HC-SR04', 'Water depth'],
  ['SW-420', 'Vibration'],
  ['LM393', 'Rainfall'],
  ['MQ-135', 'AQI / smoke'],
  ['DHT22', 'Temp / humidity'],
  ['GY-NEO6MV2', 'GPS fix'],
];

export function NodeDetail({ node, onClose, onOpenCommand }) {
  const [history, setHistory] = useState([]);
  const [hours, setHours] = useState(6);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .nodeHistory(node.id, hours)
      .then((response) => {
        if (!cancelled) setHistory(response.data.history);
      })
      .catch(() => {
        if (!cancelled) setHistory([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [node.id, hours]);

  const times = history.map((reading) => reading.timestamp);
  const factorMax = Math.max(
    1,
    ...(node.risk.topFactors ?? []).map((factor) => Number(factor.points) || 0),
  );

  return (
    <Modal
      title={node.name}
      eyebrow={`${node.id} · ${node.location}`}
      onClose={onClose}
      size="large"
      footer={
        <>
          <button className="button button--quiet" onClick={onClose}>
            Close
          </button>
          {onOpenCommand ? (
            <button
              className="button button--primary"
              onClick={() => {
                onClose();
                onOpenCommand();
              }}
            >
              <ShieldCheck size={15} />
              Open command actions
            </button>
          ) : null}
        </>
      }
    >
      <div className="node-detail">
        <div className="node-detail__hero">
          <div className="node-detail__hero-main">
            <div className="node-detail__badges">
              <RiskBadge level={node.risk.level}>{riskLabel(node.risk.level)} risk</RiskBadge>
              <span className={`link-badge link-badge--${node.health.link}`}>
                <Signal size={12} />
                {node.health.link} link
              </span>
              {node.risk.overridden ? <span className="override-chip">Authority override</span> : null}
            </div>
            <p className="node-detail__headline">{node.risk.headline}</p>
            <p className="node-detail__advisory">{node.risk.advisory}</p>
            <div className="node-detail__coordinates">
              <span>
                <LocateFixed size={13} />
                {formatCoordinate(node.lat, 'lat')}
              </span>
              <span>{formatCoordinate(node.lon, 'lon')}</span>
              <span>
                <Satellite size={13} />
                GPS fix
              </span>
            </div>
          </div>
          <RiskGauge
            score={node.risk.score}
            level={node.risk.level}
            size="small"
            label="Current index"
          />
        </div>

        <div className="node-detail__stats">
          <div>
            <span className="micro-label">Water depth</span>
            <strong>{formatNumber(node.latest.waterLevel)} cm</strong>
          </div>
          <div>
            <span className="micro-label">Rainfall</span>
            <strong>{formatNumber(node.latest.rain)} mm/h</strong>
          </div>
          <div>
            <span className="micro-label">Air quality</span>
            <strong>{formatNumber(node.latest.aqi, { maximumFractionDigits: 0 })} AQI</strong>
          </div>
          <div>
            <span className="micro-label">Battery</span>
            <strong>
              <BatteryMedium size={14} /> {formatBattery(node.latest.battery)} · {node.health.batteryPercent}%
            </strong>
          </div>
          <div>
            <span className="micro-label">Last packet</span>
            <strong>{formatRelative(node.health.lastSeen)}</strong>
          </div>
          <div>
            <span className="micro-label">Link quality</span>
            <strong>
              <Radio size={14} /> {node.latest.rssi} dBm
            </strong>
          </div>
        </div>

        <div className="node-detail__columns">
          <section className="node-detail__section">
            <div className="node-detail__section-head">
              <div>
                <span className="eyebrow">Telemetry history</span>
                <h3>Sensor traces</h3>
              </div>
              <label className="select-field select-field--inline">
                <span>Window</span>
                <select value={hours} onChange={(event) => setHours(Number(event.target.value))}>
                  <option value={6}>6 hours</option>
                  <option value={12}>12 hours</option>
                  <option value={24}>24 hours</option>
                </select>
              </label>
            </div>
            {loading ? (
              <div className="node-detail__loading">Retrieving telemetry packets…</div>
            ) : (
              <div className="history-grid">
                <HistoryChart
                  title="Water level"
                  unit="cm"
                  values={history.map((reading) => reading.waterLevel)}
                  times={times}
                />
                <HistoryChart
                  title="Rainfall"
                  unit="mm/h"
                  values={history.map((reading) => reading.rain)}
                  times={times}
                />
                <HistoryChart
                  title="Temperature"
                  unit="°C"
                  values={history.map((reading) => reading.temp)}
                  times={times}
                />
                <HistoryChart
                  title="Air quality"
                  unit="AQI"
                  values={history.map((reading) => reading.aqi)}
                  times={times}
                />
              </div>
            )}
          </section>

          <section className="node-detail__section">
            <div className="node-detail__section-head">
              <div>
                <span className="eyebrow">Risk decomposition</span>
                <h3>Contributing factors</h3>
              </div>
              <Gauge size={18} />
            </div>
            <div className="factor-list">
              {(node.risk.topFactors ?? []).map((factor) => (
                <div className="factor-row" key={`${factor.label}-${factor.value}`}>
                  <div className="factor-row__top">
                    <span>{factor.label}</span>
                    <strong>{factor.value}</strong>
                  </div>
                  <div className="factor-row__track">
                    <span style={{ width: `${Math.min(100, (factor.points / factorMax) * 100)}%` }} />
                  </div>
                  <span className="factor-row__points">+{factor.points} risk points</span>
                </div>
              ))}
            </div>

            <div className="hardware-block">
              <span className="micro-label">
                <Cpu size={12} /> Node hardware
              </span>
              <div className="hardware-grid">
                {SENSOR_SUITE.map(([code, label]) => (
                  <span className="hardware-chip" key={code}>
                    <span className="hardware-chip__dot" />
                    <strong>{code}</strong>
                    <small>{label}</small>
                  </span>
                ))}
              </div>
            </div>
          </section>
        </div>
      </div>
    </Modal>
  );
}

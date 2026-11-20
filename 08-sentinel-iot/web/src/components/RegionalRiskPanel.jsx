import { CloudRain, Droplets, Thermometer, TrendingUp, Wind } from 'lucide-react';
import { RiskGauge } from './RiskGauge.jsx';
import { formatNumber, riskLabel } from '../lib/format.js';

const LEVELS = ['low', 'moderate', 'high', 'severe'];

export function RegionalRiskPanel({ snapshot }) {
  const { summary, weather, nodes } = snapshot;
  const peakNode = nodes.find((node) => node.id === summary.peakNode?.id);
  const total = Math.max(1, summary.nodesTotal);

  return (
    <section className="panel risk-panel">
      <header className="panel__head">
        <div>
          <span className="eyebrow">Risk synthesis</span>
          <h2>Regional risk</h2>
        </div>
        <span className="risk-panel__live">
          <TrendingUp size={13} />
          Live
        </span>
      </header>

      <div className="risk-panel__hero">
        <RiskGauge
          score={summary.peakRisk}
          level={summary.peakRiskLevel}
          label="Peak node index"
          showFactors
        />
        <div className="risk-panel__hero-copy">
          <span className="micro-label">Highest exposure</span>
          <strong>{peakNode?.name ?? 'No node data'}</strong>
          <span>{peakNode ? riskLabel(peakNode.risk.level) : '—'} risk condition</span>
          <div className="risk-panel__hero-divider" />
          <span className="micro-label">Population in risk envelope</span>
          <strong className="risk-panel__population">
            {formatNumber(summary.affectedPopulation, { maximumFractionDigits: 0 })}
          </strong>
          <span>residents across high-risk sectors</span>
        </div>
      </div>

      <div className="risk-spectrum">
        <div className="risk-spectrum__head">
          <span className="micro-label">Node distribution</span>
          <span className="mono-tiny">{summary.nodesTotal} nodes</span>
        </div>
        <div className="risk-spectrum__bar">
          {LEVELS.map((level) => {
            const count = summary.riskDistribution[level] ?? 0;
            if (!count) return null;
            return (
              <span
                key={level}
                className={`risk-spectrum__segment risk-spectrum__segment--${level}`}
                style={{ width: `${(count / total) * 100}%` }}
                title={`${count} ${riskLabel(level)}`}
              />
            );
          })}
        </div>
        <div className="risk-spectrum__legend">
          {LEVELS.map((level) => (
            <span key={level} className={`risk-spectrum__legend-item risk-spectrum__legend-item--${level}`}>
              <span />
              {riskLabel(level)}
              <strong>{summary.riskDistribution[level] ?? 0}</strong>
            </span>
          ))}
        </div>
      </div>

      <div className="weather-grid">
        <div className="weather-tile">
          <span className="weather-tile__icon">
            <Thermometer size={15} />
          </span>
          <span className="micro-label">Temp</span>
          <strong>{formatNumber(weather.temp)}°</strong>
        </div>
        <div className="weather-tile">
          <span className="weather-tile__icon">
            <Droplets size={15} />
          </span>
          <span className="micro-label">Humidity</span>
          <strong>{formatNumber(weather.humidity, { maximumFractionDigits: 0 })}%</strong>
        </div>
        <div className="weather-tile">
          <span className="weather-tile__icon">
            <CloudRain size={15} />
          </span>
          <span className="micro-label">Rain</span>
          <strong>{formatNumber(weather.rain)}</strong>
        </div>
        <div className="weather-tile">
          <span className="weather-tile__icon">
            <Wind size={15} />
          </span>
          <span className="micro-label">AQI</span>
          <strong>{formatNumber(weather.aqi, { maximumFractionDigits: 0 })}</strong>
        </div>
      </div>
      <p className="risk-panel__footnote">
        Network mean index {summary.averageRisk}/100 · {summary.nodesOnline}/{summary.nodesTotal} nodes online ·
        update rate 4 s
      </p>
    </section>
  );
}

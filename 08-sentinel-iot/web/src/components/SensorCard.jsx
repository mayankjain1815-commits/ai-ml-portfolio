import {
  Activity,
  ArrowUpRight,
  BatteryMedium,
  CloudRain,
  Droplets,
  Radio,
  Thermometer,
  Waves,
  Wind,
} from 'lucide-react';
import { RiskBadge } from './RiskBadge.jsx';
import { Sparkline } from './Sparkline.jsx';
import {
  batteryTone,
  formatBattery,
  formatNumber,
  formatRelative,
  riskLabel,
} from '../lib/format.js';

function VibrationState({ active }) {
  return (
    <div className={`vibration-state ${active ? 'vibration-state--active' : ''}`}>
      <div className="vibration-state__bars" aria-hidden="true">
        {[0, 1, 2, 3, 4].map((bar) => (
          <span key={bar} style={{ '--bar-index': bar }} />
        ))}
      </div>
      <span>{active ? 'Ground movement' : 'Seismic stable'}</span>
    </div>
  );
}

export function SensorCard({ node, onInspect }) {
  const { latest, risk, health, trends } = node;
  const overridden = Boolean(risk.overridden);

  return (
    <article className={`sensor-card sensor-card--${risk.level}`}>
      <div className="sensor-card__top">
        <div className="sensor-card__identity">
          <span className="mono-tiny sensor-card__id">{node.id}</span>
          <span className={`sensor-card__link sensor-card__link--${health.link}`}>
            <Radio size={11} />
            {health.link}
          </span>
        </div>
        <RiskBadge level={risk.level}>{overridden ? 'Override' : riskLabel(risk.level)}</RiskBadge>
      </div>

      <div className="sensor-card__heading">
        <div>
          <h3>{node.name}</h3>
          <p>{node.location}</p>
        </div>
        <button
          className="sensor-card__inspect"
          onClick={() => onInspect(node.id)}
          aria-label={`Inspect ${node.name}`}
        >
          <ArrowUpRight size={17} />
        </button>
      </div>

      <div className="sensor-card__water">
        <div>
          <span className="sensor-card__metric-label">
            <Waves size={13} />
            Water depth
          </span>
          <div className="sensor-card__water-value">
            <strong>{formatNumber(latest.waterLevel)}</strong>
            <span>cm</span>
          </div>
        </div>
        <div className="sensor-card__spark">
          <Sparkline
            values={trends?.water ?? []}
            height={42}
            ariaLabel={`${node.name} water level trend`}
          />
          <span className="sensor-card__spark-caption">
            {risk.hazards?.find((hazard) => hazard.key === 'flood')?.trend?.direction === 'rising'
              ? 'Rising'
              : 'Last 30 packets'}
          </span>
        </div>
      </div>

      <div className="sensor-card__grid">
        <div className="sensor-card__metric">
          <span className="sensor-card__metric-label">
            <CloudRain size={13} />
            Rain
          </span>
          <strong>
            {formatNumber(latest.rain)} <small>mm/h</small>
          </strong>
        </div>
        <div className="sensor-card__metric">
          <span className="sensor-card__metric-label">
            <Wind size={13} />
            AQI
          </span>
          <strong>
            {formatNumber(latest.aqi, { maximumFractionDigits: 0 })}
            <small> index</small>
          </strong>
        </div>
        <div className="sensor-card__metric">
          <span className="sensor-card__metric-label">
            <Thermometer size={13} />
            Temp
          </span>
          <strong>
            {formatNumber(latest.temp)} <small>°C</small>
          </strong>
        </div>
        <div className="sensor-card__metric">
          <span className="sensor-card__metric-label">
            <Droplets size={13} />
            Humidity
          </span>
          <strong>
            {formatNumber(latest.humidity, { maximumFractionDigits: 0 })} <small>%</small>
          </strong>
        </div>
      </div>

      <div className="sensor-card__footer">
        <VibrationState active={latest.vibration} />
        <div className={`sensor-card__battery sensor-card__battery--${batteryTone(health.batteryPercent)}`}>
          <BatteryMedium size={15} />
          <span>
            <strong>{health.batteryPercent}%</strong>
            {formatBattery(latest.battery)}
          </span>
        </div>
      </div>

      <div className="sensor-card__signal-bar">
        <span className={`sensor-card__signal sensor-card__signal--${risk.level}`}>
          <Activity size={11} />
          {overridden ? `${risk.sensorLevel} sensor · ${risk.level} override` : risk.headline}
        </span>
        <span className="sensor-card__packet">{formatRelative(health.lastSeen)}</span>
      </div>
    </article>
  );
}

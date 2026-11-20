import { riskLabel } from '../lib/format.js';

const RADIUS = 58;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function RiskGauge({
  score = 0,
  level = 'low',
  size = 'large',
  label = 'Composite risk',
  showFactors = false,
  className = '',
}) {
  const normalizedScore = Math.min(100, Math.max(0, Number(score) || 0));
  const progress = (normalizedScore / 100) * CIRCUMFERENCE;

  return (
    <div className={`risk-gauge risk-gauge--${size} risk-gauge--${level} ${className}`}>
      <div className="risk-gauge__visual">
        <svg viewBox="0 0 160 160" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow={normalizedScore}>
          <circle className="risk-gauge__ticks" cx="80" cy="80" r="72" />
          <circle className="risk-gauge__track" cx="80" cy="80" r={RADIUS} />
          <circle
            className="risk-gauge__progress"
            cx="80"
            cy="80"
            r={RADIUS}
            strokeDasharray={`${progress} ${CIRCUMFERENCE}`}
          />
        </svg>
        <div className="risk-gauge__readout">
          <span className="risk-gauge__score">{Math.round(normalizedScore)}</span>
          <span className="risk-gauge__denominator">/ 100</span>
        </div>
        {level === 'severe' ? <span className="risk-gauge__pulse" /> : null}
      </div>
      <div className="risk-gauge__caption">
        <span className="risk-gauge__label">{label}</span>
        <span className={`risk-gauge__level risk-gauge__level--${level}`}>{riskLabel(level)}</span>
      </div>
      {showFactors ? <span className="risk-gauge__hint">Weighted sensor index</span> : null}
    </div>
  );
}

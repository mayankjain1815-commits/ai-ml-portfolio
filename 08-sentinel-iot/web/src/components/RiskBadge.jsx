import { riskLabel } from '../lib/format.js';

export function RiskBadge({ level = 'low', children, compact = false, className = '' }) {
  return (
    <span
      className={`risk-badge risk-badge--${level} ${compact ? 'risk-badge--compact' : ''} ${className}`}
    >
      <span className="risk-badge__dot" />
      {children ?? riskLabel(level)}
    </span>
  );
}

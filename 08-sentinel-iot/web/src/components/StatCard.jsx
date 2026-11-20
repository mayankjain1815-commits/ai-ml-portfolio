export function StatCard({
  label,
  value,
  suffix,
  detail,
  icon: Icon,
  tone = 'default',
  children,
  className = '',
  onClick,
  clickable,
}) {
  const isClickable = clickable || typeof onClick === 'function';
  return (
    <article
      className={`stat-card stat-card--${tone} ${className} ${isClickable ? 'stat-card--clickable' : ''}`}
      onClick={onClick}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={(e) => {
        if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onClick?.();
        }
      }}
    >
      <div className="stat-card__top">
        <span className="micro-label">{label}</span>
        {Icon ? (
          <span className="stat-card__icon">
            <Icon size={16} strokeWidth={1.7} />
          </span>
        ) : null}
      </div>
      <div className="stat-card__value-row">
        <span className="stat-card__value">{value}</span>
        {suffix ? <span className="stat-card__suffix">{suffix}</span> : null}
      </div>
      {detail ? <p className="stat-card__detail">{detail}</p> : null}
      {children ? <div className="stat-card__body">{children}</div> : null}
    </article>
  );
}

export function Sparkline({
  values = [],
  height = 36,
  className = '',
  ariaLabel = 'Trend',
  showArea = true,
  showEndPoint = true,
}) {
  const numericValues = values
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value));

  if (numericValues.length < 2) {
    return <div className={`sparkline sparkline--empty ${className}`} style={{ height }} aria-hidden="true" />;
  }

  const width = 220;
  const padding = 3;
  const min = Math.min(...numericValues);
  const max = Math.max(...numericValues);
  const range = max - min || 1;
  const step = (width - padding * 2) / (numericValues.length - 1);

  const points = numericValues.map((value, index) => {
    const x = padding + index * step;
    const y = height - padding - ((value - min) / range) * (height - padding * 2);
    return [Number(x.toFixed(2)), Number(y.toFixed(2))];
  });

  const line = points.map(([x, y], index) => `${index === 0 ? 'M' : 'L'}${x},${y}`).join(' ');
  const area = `${line} L${points.at(-1)[0]},${height} L${points[0][0]},${height} Z`;
  const last = points.at(-1);

  return (
    <svg
      className={`sparkline ${className}`}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      role="img"
      aria-label={ariaLabel}
    >
      {showArea ? <path className="sparkline__area" d={area} /> : null}
      <path className="sparkline__line" d={line} vectorEffect="non-scaling-stroke" />
      {showEndPoint ? <circle className="sparkline__end" cx={last[0]} cy={last[1]} r="2.6" /> : null}
    </svg>
  );
}

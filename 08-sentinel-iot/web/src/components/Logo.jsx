export function SentinelMark({ size = 42 }) {
  return (
    <svg
      className="sentinel-mark"
      width={size}
      height={size}
      viewBox="0 0 48 48"
      role="img"
      aria-label="Sentinel"
    >
      <circle className="sentinel-mark__orbit" cx="24" cy="24" r="21" />
      <circle className="sentinel-mark__orbit sentinel-mark__orbit--inner" cx="24" cy="24" r="14" />
      <path
        className="sentinel-mark__shield"
        d="M24 9.5 36 15v9.3c0 7.1-4.7 11.8-12 14.2-7.3-2.4-12-7.1-12-14.2V15L24 9.5Z"
      />
      <path className="sentinel-mark__signal" d="M19 23.3a7 7 0 0 1 10 0" />
      <path className="sentinel-mark__signal" d="M21.5 26.1a3.5 3.5 0 0 1 5 0" />
      <circle className="sentinel-mark__core" cx="24" cy="30" r="1.6" />
      <path className="sentinel-mark__needle" d="M24 9.5V6.5M43.2 24h2.3M24 41.5v2.3M2.5 24h2.3" />
    </svg>
  );
}

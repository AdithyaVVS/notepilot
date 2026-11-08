export function Mark({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <rect x="4" y="3" width="24" height="26" rx="3" fill="#fff" stroke="#16213E" strokeWidth="2" />
      <rect x="7" y="12" width="18" height="6" rx="1" fill="#FFD84A" />
      <path d="M8 9h12M8 15h16M8 22h9" stroke="#16213E" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <span className="wordmark">
      <Mark />
      NotePilot
    </span>
  );
}

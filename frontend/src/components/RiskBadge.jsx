export function RiskBadge({ level }) {
  return <span className={`risk-badge ${level}`}>{level}</span>;
}


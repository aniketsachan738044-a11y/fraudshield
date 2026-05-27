export function ScoreBar({ score }) {
  const value = Math.max(0, Math.min(100, Number(score) || 0));
  return (
    <div className="score-wrap" aria-label={`Risk score ${value}`}>
      <div className="score-track">
        <span className="score-fill" style={{ width: `${value}%` }} />
      </div>
      <strong>{value.toFixed(1)}</strong>
    </div>
  );
}


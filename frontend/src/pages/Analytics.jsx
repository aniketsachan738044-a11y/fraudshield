import { Activity, AlertTriangle, BarChart3, IndianRupee, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client.js";

export function Analytics() {
  const [summary, setSummary] = useState(null);
  const [breakdown, setBreakdown] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState("");
  const [retraining, setRetraining] = useState(false);
  const [retrainNotice, setRetrainNotice] = useState("");

  async function handleRetrain() {
    setRetraining(true);
    setRetrainNotice("");
    try {
      const res = await api.retrainModel();
      setMetrics((prev) => ({
        ...prev,
        accuracy: res.accuracy,
        precision: res.precision,
        recall: res.recall,
        f1_score: res.f1_score,
      }));
      setRetrainNotice(res.message);
    } catch (err) {
      setError(err.message);
    } finally {
      setRetraining(false);
    }
  }

  useEffect(() => {
    let cancelled = false;

    async function loadAnalytics() {
      try {
        const [summaryData, breakdownData, metricData] = await Promise.all([
          api.summary(),
          api.riskBreakdown(),
          api.modelMetrics(),
        ]);
        if (!cancelled) {
          setSummary(summaryData);
          setBreakdown(breakdownData);
          setMetrics(metricData);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadAnalytics();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <section className="panel">
        <div className="skeleton-list">
          {Array.from({ length: 7 }).map((_, index) => (
            <span key={index} />
          ))}
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="panel">
        <p className="error-text">{error}</p>
      </section>
    );
  }

  const total = breakdown.reduce((sum, item) => sum + item.count, 0) || 1;

  return (
    <div className="analytics-stack">
      <section className="metric-grid">
        <article className="metric-card">
          <Activity size={22} />
          <span>Total transactions</span>
          <strong>{summary.total_transactions}</strong>
        </article>
        <article className="metric-card">
          <IndianRupee size={22} />
          <span>Total amount</span>
          <strong>{Number(summary.total_amount).toLocaleString("en-IN")}</strong>
        </article>
        <article className="metric-card">
          <BarChart3 size={22} />
          <span>Average risk</span>
          <strong>{summary.average_risk_score}</strong>
        </article>
        <article className="metric-card warning">
          <AlertTriangle size={22} />
          <span>High risk</span>
          <strong>{summary.high_risk_count}</strong>
        </article>
      </section>

      <section className="panel two-column">
        <div>
          <div className="section-heading">
            <p className="eyebrow">Distribution</p>
            <h1>Risk breakdown</h1>
          </div>

          <div className="bar-list">
            {breakdown.map((item) => (
              <div key={item.label} className="bar-row">
                <span>{item.label}</span>
                <div>
                  <i className={item.label} style={{ width: `${(item.count / total) * 100}%` }} />
                </div>
                <strong>{item.count}</strong>
              </div>
            ))}
          </div>

          <div className="chart-container">
            <svg viewBox="0 0 300 120" className="chart-svg">
              {breakdown.map((item, idx) => {
                const colors = { low: "#10b981", medium: "#f59e0b", high: "#ef4444" };
                const barHeight = Math.max(12, Math.min(85, (item.count / total) * 90));
                const x = 45 + idx * 85;
                const y = 95 - barHeight;
                return (
                  <g key={item.label}>
                    <rect x={x} y={y} width="55" height={barHeight} fill={colors[item.label] || "#6b7280"} rx="4" />
                    <text x={x + 27} y={y - 6} textAnchor="middle" fontSize="12" fill="#374151" fontWeight="600">
                      {item.count}
                    </text>
                    <text x={x + 27} y="112" textAnchor="middle" fontSize="11" fill="#6b7280" textTransform="capitalize">
                      {item.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        </div>

        <div>
          <div className="section-heading" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <p className="eyebrow">Evaluation</p>
              <h2>Model metrics</h2>
            </div>
            <button
              className="icon-text-btn dark"
              style={{ fontSize: "0.82rem", padding: "5px 12px" }}
              onClick={handleRetrain}
              disabled={retraining}
            >
              {retraining ? "Training..." : "Retrain ML Model"}
            </button>
          </div>

          {retrainNotice && (
            <p className="success-text" style={{ fontSize: "0.82rem", margin: "6px 0 10px 0" }}>
              {retrainNotice}
            </p>
          )}

          <div className="metrics-list">
            <span>Accuracy <strong>{metrics.accuracy}</strong></span>
            <span>Precision <strong>{metrics.precision}</strong></span>
            <span>Recall <strong>{metrics.recall}</strong></span>
            <span>F1-score <strong>{metrics.f1_score}</strong></span>
          </div>


          {metrics.confusion_matrix && metrics.confusion_matrix.length === 2 && (
            <div className="confusion-matrix-box" style={{ marginTop: "14px" }}>
              <p className="eyebrow" style={{ marginBottom: "6px" }}>Confusion Matrix (Test Split)</p>
              <table style={{ width: "100%", fontSize: "12.5px", borderCollapse: "collapse", textAlign: "center" }}>
                <thead>
                  <tr style={{ background: "#f3f4f6" }}>
                    <th style={{ padding: "6px" }}>Actual \ Pred</th>
                    <th style={{ padding: "6px", color: "#10b981" }}>Pred Legitimate</th>
                    <th style={{ padding: "6px", color: "#ef4444" }}>Pred Fraud</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style={{ fontWeight: "600", padding: "6px" }}>Actual Legitimate</td>
                    <td style={{ padding: "6px", background: "#f0fdf4", fontWeight: "600" }}>{metrics.confusion_matrix[0][0]} (TN)</td>
                    <td style={{ padding: "6px", background: "#fef2f2" }}>{metrics.confusion_matrix[0][1]} (FP)</td>
                  </tr>
                  <tr>
                    <td style={{ fontWeight: "600", padding: "6px" }}>Actual Fraud</td>
                    <td style={{ padding: "6px", background: "#fef2f2" }}>{metrics.confusion_matrix[1][0]} (FN)</td>
                    <td style={{ padding: "6px", background: "#fef2f2", fontWeight: "600" }}>{metrics.confusion_matrix[1][1]} (TP)</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          <div className="note-box" style={{ marginTop: "14px" }}>
            <ShieldCheck size={18} />
            <p>{metrics.note}</p>
          </div>
        </div>
      </section>
    </div>
  );
}


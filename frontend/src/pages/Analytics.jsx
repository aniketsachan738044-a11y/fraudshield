import { Activity, AlertTriangle, BarChart3, IndianRupee, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client.js";

export function Analytics() {
  const [summary, setSummary] = useState(null);
  const [breakdown, setBreakdown] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

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
        </div>

        <div>
          <div className="section-heading">
            <p className="eyebrow">Evaluation</p>
            <h2>Model metrics</h2>
          </div>

          <div className="metrics-list">
            <span>Accuracy <strong>{metrics.accuracy}</strong></span>
            <span>Precision <strong>{metrics.precision}</strong></span>
            <span>Recall <strong>{metrics.recall}</strong></span>
            <span>F1-score <strong>{metrics.f1_score}</strong></span>
          </div>
          <div className="note-box">
            <ShieldCheck size={18} />
            <p>{metrics.note}</p>
          </div>
        </div>
      </section>
    </div>
  );
}


import { Download, FileText, Filter, RefreshCw, Search, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api, downloadCsv, downloadPdf } from "../api/client.js";
import { RiskBadge } from "../components/RiskBadge.jsx";
import { ScoreBar } from "../components/ScoreBar.jsx";

export function Dashboard() {
  const [transactions, setTransactions] = useState([]);
  const [riskLevel, setRiskLevel] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [exporting, setExporting] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);

  async function loadTransactions() {
    setLoading(true);
    setError("");
    setNotice("");
    try {
      const data = await api.transactions({ risk_level: riskLevel, search });
      setTransactions(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTransactions();
  }, [riskLevel]);

  async function handleExport() {
    setExporting(true);
    setError("");
    setNotice("");
    try {
      await downloadCsv();
    } catch (err) {
      setError(err.message);
    } finally {
      setExporting(false);
    }
  }

  async function handleExportPdf() {
    setExportingPdf(true);
    setError("");
    setNotice("");
    try {
      await downloadPdf();
    } catch (err) {
      setError(err.message);
    } finally {
      setExportingPdf(false);
    }
  }

  async function handleToggleFraud(id, isFraud) {
    try {
      const updated = await api.submitFeedback(id, {
        is_fraud: isFraud,
        note: isFraud ? "Customer chargeback confirmed" : "Verified legitimate",
      });
      setTransactions((prev) => prev.map((t) => (t.id === id ? updated : t)));
      setNotice(`Transaction #${id} audit status updated: ${isFraud ? "Confirmed Fraud" : "Clean"}`);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleClear() {
    const confirmed = window.confirm("Clear all saved transactions for this account?");
    if (!confirmed) return;

    setLoading(true);
    setError("");
    setNotice("");
    try {
      await api.clearTransactions();
      setTransactions([]);
      setNotice("Dashboard history cleared");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel wide-panel">
      <div className="table-toolbar">
        <div className="section-heading">
          <p className="eyebrow">History</p>
          <h1>Transaction dashboard</h1>
        </div>

        <div className="toolbar-actions">
          <div className="search-box">
            <Search size={17} />
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search receiver" />
          </div>
          <select value={riskLevel} onChange={(event) => setRiskLevel(event.target.value)} aria-label="Filter risk">
            <option value="">All risk</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
          <button className="icon-text-btn" onClick={loadTransactions} disabled={loading}>
            <RefreshCw size={17} />
            Refresh
          </button>
          <button className="icon-text-btn dark" onClick={handleExport} disabled={exporting}>
            <Download size={17} />
            CSV
          </button>
          <button className="icon-text-btn dark" onClick={handleExportPdf} disabled={exportingPdf}>
            <FileText size={17} />
            PDF Report
          </button>
          <button className="icon-text-btn danger" onClick={handleClear} disabled={loading || transactions.length === 0}>
            <Trash2 size={17} />
            Clear
          </button>
        </div>
      </div>

      {error && <p className="error-text">{error}</p>}
      {notice && <p className="success-text">{notice}</p>}

      {loading ? (
        <div className="skeleton-list">
          {Array.from({ length: 6 }).map((_, index) => (
            <span key={index} />
          ))}
        </div>
      ) : transactions.length === 0 ? (
        <div className="empty-state table-empty">
          <Filter size={28} />
          <p>No transactions match the current filters.</p>
        </div>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Receiver</th>
                <th>Type</th>
                <th>Amount</th>
                <th>Risk</th>
                <th>Score</th>
                <th>Top reason</th>
                <th>Audit Feedback</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((tx) => (
                <tr key={tx.id}>
                  <td>
                    <strong>{tx.receiver_id}</strong>
                    <span>{tx.location_city ? `${tx.channel.replace("_", " ")} • ${tx.location_city}` : tx.channel.replace("_", " ")}</span>
                  </td>
                  <td>{tx.transaction_type.replace("_", " ")}</td>
                  <td>₹ {Number(tx.amount).toLocaleString("en-IN")}</td>
                  <td>
                    <RiskBadge level={tx.risk_level} />
                  </td>
                  <td>
                    <ScoreBar score={tx.risk_score} />
                  </td>
                  <td>{tx.explanations?.[0]?.title || "Normal pattern"}</td>
                  <td>
                    {tx.is_fraud_confirmed === true ? (
                      <span
                        style={{
                          fontSize: "0.72rem",
                          fontWeight: 700,
                          padding: "2px 6px",
                          borderRadius: "4px",
                          background: "#fee2e2",
                          color: "#dc2626",
                          cursor: "pointer",
                        }}
                        onClick={() => handleToggleFraud(tx.id, false)}
                        title="Click to reset"
                      >
                        CONFIRMED FRAUD
                      </span>
                    ) : (
                      <button
                        className="ghost-btn"
                        style={{ fontSize: "0.75rem", padding: "2px 8px", border: "1px solid #cbd5e1", borderRadius: "4px" }}
                        onClick={() => handleToggleFraud(tx.id, true)}
                        title="Mark as confirmed chargeback / fraud"
                      >
                        Flag Fraud
                      </button>
                    )}
                  </td>
                  <td>{new Date(tx.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

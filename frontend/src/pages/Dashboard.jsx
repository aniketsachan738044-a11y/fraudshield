import { Download, Filter, RefreshCw, Search, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api, downloadCsv } from "../api/client.js";
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
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((tx) => (
                <tr key={tx.id}>
                  <td>
                    <strong>{tx.receiver_id}</strong>
                    <span>{tx.channel.replace("_", " ")}</span>
                  </td>
                  <td>{tx.transaction_type.replace("_", " ")}</td>
                  <td>Rs {Number(tx.amount).toLocaleString("en-IN")}</td>
                  <td>
                    <RiskBadge level={tx.risk_level} />
                  </td>
                  <td>
                    <ScoreBar score={tx.risk_score} />
                  </td>
                  <td>{tx.explanations?.[0]?.title || "Normal pattern"}</td>
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

import { Ban, CheckCircle2, Globe, PlusCircle, RefreshCw, ShieldAlert, Trash2, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client.js";

const BUILTIN_RULES = [
  {
    id: "impossible_travel",
    title: "Impossible Travel Velocity",
    category: "GeoIP Kinematics",
    threshold: "Speed > 800 km/h between locations",
    action: "Auto-escalate to High Risk (Score +45, Floor 92)",
    status: "Active",
  },
  {
    id: "mule_structuring",
    title: "Mule Fan-Out & Structuring",
    category: "Graph & Topology",
    threshold: ">= 3 distinct receivers within 15 mins",
    action: "Auto-escalate to High Risk (Score +40, Floor 88)",
    status: "Active",
  },
  {
    id: "velocity_bursts",
    title: "Sliding-Window Velocity Bursts",
    category: "Temporal Heuristics",
    threshold: ">= 3 tx in 5m or >= 5 tx in 1 hour",
    action: "Score +30 / +20 & Step-Up 2FA Challenge",
    status: "Active",
  },
  {
    id: "spending_spike",
    title: "Baseline Spending Outlier",
    category: "Behavioral Profiling",
    threshold: "Amount > 3.0x 30-day user average",
    action: "Score +25 & Step-Up Review",
    status: "Active",
  },
  {
    id: "blocklist_enforcement",
    title: "Counterparty Blocklist Match",
    category: "Deterministic Sanction",
    threshold: "Exact match on blocked receiver ID or IP",
    action: "Instant Hard Block (Score 100)",
    status: "Active",
  },
];

export function RuleStudio() {
  const [blocklist, setBlocklist] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [entryType, setEntryType] = useState("receiver_id");
  const [value, setValue] = useState("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function loadBlocklist() {
    setLoading(true);
    setError("");
    try {
      const data = await api.listBlocklist();
      setBlocklist(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadBlocklist();
  }, []);

  async function handleAdd(e) {
    e.preventDefault();
    if (!value.trim() || !reason.trim()) return;

    setSubmitting(true);
    setError("");
    setNotice("");
    try {
      const created = await api.addBlocklist({
        entry_type: entryType,
        value: value.trim(),
        reason: reason.trim(),
      });
      setBlocklist((prev) => [created, ...prev]);
      setValue("");
      setReason("");
      setNotice(`Added "${created.value}" to blocklist`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id, val) {
    if (!window.confirm(`Remove "${val}" from the blocklist?`)) return;
    setError("");
    setNotice("");
    try {
      await api.deleteBlocklist(id);
      setBlocklist((prev) => prev.filter((item) => item.id !== id));
      setNotice(`Removed "${val}" from blocklist`);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="two-column-layout">
      {/* Left Column: Built-in Rules & Engine Status */}
      <section className="panel">
        <div className="section-heading">
          <p className="eyebrow">Detection Pipeline</p>
          <h1>Active Risk Rules</h1>
        </div>

        <p className="muted-text" style={{ marginBottom: "1.2rem", fontSize: "0.9rem" }}>
          FraudShield evaluates both ML anomaly probabilities and deterministic zero-tolerance risk rules on every payment intent.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
          {BUILTIN_RULES.map((rule) => (
            <div
              key={rule.id}
              style={{
                background: "var(--card-bg, #ffffff)",
                border: "1px solid var(--border-color, #e2e8f0)",
                borderRadius: "8px",
                padding: "1rem",
                display: "flex",
                flexDirection: "column",
                gap: "0.4rem",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontWeight: 600, fontSize: "0.95rem", color: "var(--text-color, #0f172a)" }}>
                  {rule.title}
                </span>
                <span
                  style={{
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    padding: "2px 8px",
                    borderRadius: "999px",
                    background: "#dcfce7",
                    color: "#166534",
                  }}
                >
                  {rule.status}
                </span>
              </div>
              <p style={{ margin: 0, fontSize: "0.82rem", color: "#64748b" }}>
                <strong>Condition:</strong> {rule.threshold}
              </p>
              <p style={{ margin: 0, fontSize: "0.82rem", color: "#2563eb" }}>
                <strong>Enforcement:</strong> {rule.action}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Right Column: Blocklist Manager */}
      <section className="panel">
        <div className="table-toolbar" style={{ marginBottom: "1rem" }}>
          <div className="section-heading">
            <p className="eyebrow">Sanctions & Blacklists</p>
            <h1>Counterparty Blocklist</h1>
          </div>
          <button className="icon-text-btn" onClick={loadBlocklist} disabled={loading}>
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>

        {error && <p className="error-text">{error}</p>}
        {notice && <p className="success-text">{notice}</p>}

        {/* Add Entry Form */}
        <form
          onSubmit={handleAdd}
          style={{
            background: "var(--card-bg, #f8fafc)",
            border: "1px solid #e2e8f0",
            borderRadius: "8px",
            padding: "1rem",
            marginBottom: "1.2rem",
            display: "flex",
            flexDirection: "column",
            gap: "0.75rem",
          }}
        >
          <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>Add Blocklist Record</span>
          <div style={{ display: "grid", gridTemplateColumns: "130px 1fr", gap: "0.6rem" }}>
            <select
              value={entryType}
              onChange={(e) => setEntryType(e.target.value)}
              style={{ padding: "0.45rem", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "0.85rem" }}
            >
              <option value="receiver_id">Receiver ID / VPA</option>
              <option value="ip_address">IP Address</option>
            </select>
            <input
              type="text"
              placeholder={entryType === "receiver_id" ? "e.g. scammer@fakeupi or VPA-9988" : "e.g. 198.51.100.44"}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              required
              style={{ padding: "0.45rem 0.65rem", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "0.85rem" }}
            />
          </div>
          <input
            type="text"
            placeholder="Reason (e.g., Reported mule account, known botnet proxy)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required
            style={{ padding: "0.45rem 0.65rem", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "0.85rem" }}
          />
          <button
            type="submit"
            className="icon-text-btn"
            disabled={submitting}
            style={{ alignSelf: "flex-start", background: "#0f172a", color: "#fff" }}
          >
            <PlusCircle size={16} />
            {submitting ? "Saving..." : "Add to Blocklist"}
          </button>
        </form>

        {/* Blocklist Records Table */}
        {loading ? (
          <div className="skeleton-list">
            {Array.from({ length: 4 }).map((_, i) => (
              <span key={i} />
            ))}
          </div>
        ) : blocklist.length === 0 ? (
          <div className="empty-state" style={{ padding: "2rem 1rem", textAlign: "center", color: "#64748b" }}>
            <Ban size={32} style={{ marginBottom: "0.5rem", opacity: 0.5 }} />
            <p>No active blocklist records. Add suspicious counterparties above.</p>
          </div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Target Value</th>
                  <th>Reason</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {blocklist.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <span
                        style={{
                          fontSize: "0.75rem",
                          fontWeight: 600,
                          padding: "2px 6px",
                          borderRadius: "4px",
                          background: item.entry_type === "ip_address" ? "#e0e7ff" : "#fee2e2",
                          color: item.entry_type === "ip_address" ? "#3730a3" : "#991b1b",
                        }}
                      >
                        {item.entry_type === "ip_address" ? "IP" : "RECEIVER"}
                      </span>
                    </td>
                    <td>
                      <strong>{item.value}</strong>
                    </td>
                    <td style={{ fontSize: "0.82rem", color: "#475569" }}>{item.reason}</td>
                    <td>
                      <button
                        className="icon-text-btn danger"
                        onClick={() => handleDelete(item.id, item.value)}
                        style={{ padding: "3px 8px", fontSize: "0.78rem" }}
                        title="Delete"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
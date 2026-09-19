import { AlertOctagon, CheckCircle, Copy, FileText, Filter, Network, RefreshCw, ShieldAlert, User, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client.js";

export function NetworkGraph() {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [], mule_clusters_detected: 0, high_risk_connections: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedNode, setSelectedNode] = useState(null);
  const [filterType, setFilterType] = useState("all");

  // AI Copilot / SAR modal state
  const [sarData, setSarData] = useState(null);
  const [sarLoading, setSarLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  async function loadGraph() {
    setLoading(true);
    setError("");
    try {
      const data = await api.networkGraph();
      setGraphData(data);
      if (data.nodes.length > 0 && !selectedNode) {
        setSelectedNode(data.nodes[0]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadGraph();
  }, []);

  async function handleGenerateSAR(transactionId = null) {
    setSarLoading(true);
    try {
      const res = await api.investigateCase({ transaction_id: transactionId });
      setSarData(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setSarLoading(false);
    }
  }

  function handleCopySAR() {
    if (!sarData) return;
    navigator.clipboard.writeText(sarData.formal_sar_narrative);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const filteredNodes = graphData.nodes.filter((n) => {
    if (filterType === "mule") return n.type === "mule" || n.type === "blocked";
    if (filterType === "high_risk") return n.risk_score >= 65;
    return true;
  });

  // Layout calculation for SVG rendering
  const width = 640;
  const height = 480;
  const centerX = width / 2;
  const centerY = height / 2;

  const senderNode = graphData.nodes.find((n) => n.type === "sender");
  const otherNodes = filteredNodes.filter((n) => n.type !== "sender");

  const positionedNodes = otherNodes.map((node, index) => {
    const angle = (index / Math.max(1, otherNodes.length)) * 2 * Math.PI - Math.PI / 2;
    const radius = 170;
    return {
      ...node,
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    };
  });

  if (senderNode) {
    positionedNodes.push({
      ...senderNode,
      x: centerX,
      y: centerY,
    });
  }

  const nodeMap = new Map(positionedNodes.map((n) => [n.id, n]));

  return (
    <div className="analytics-stack">
      {/* Metrics Row */}
      <section className="metric-grid">
        <article className="metric-card">
          <Network size={22} />
          <span>Active Entities</span>
          <strong>{graphData.nodes.length}</strong>
        </article>
        <article className="metric-card">
          <Zap size={22} />
          <span>Total Link Edges</span>
          <strong>{graphData.edges.length}</strong>
        </article>
        <article className="metric-card warning">
          <AlertOctagon size={22} />
          <span>Mule Rings Detected</span>
          <strong>{graphData.mule_clusters_detected}</strong>
        </article>
        <article className="metric-card danger">
          <ShieldAlert size={22} />
          <span>High-Risk Connections</span>
          <strong>{graphData.high_risk_connections}</strong>
        </article>
      </section>

      {/* Main Two-Column View */}
      <div className="two-column-layout">
        {/* Left Column: Visual Graph */}
        <section className="panel" style={{ position: "relative" }}>
          <div className="table-toolbar" style={{ marginBottom: "1rem" }}>
            <div className="section-heading">
              <p className="eyebrow">Topology</p>
              <h1>Mule Network Visualizer</h1>
            </div>
            <div className="toolbar-actions">
              <select value={filterType} onChange={(e) => setFilterType(e.target.value)} aria-label="Filter Graph">
                <option value="all">All Entities</option>
                <option value="mule">Mule & Blocked Only</option>
                <option value="high_risk">High Risk (&gt;=65)</option>
              </select>
              <button className="icon-text-btn" onClick={loadGraph} disabled={loading}>
                <RefreshCw size={16} />
                Refresh
              </button>
            </div>
          </div>

          {error && <p className="error-text">{error}</p>}

          {loading ? (
            <div className="skeleton-list">
              {Array.from({ length: 5 }).map((_, i) => (
                <span key={i} />
              ))}
            </div>
          ) : (
            <div style={{ background: "#0f172a", borderRadius: "8px", overflow: "hidden", position: "relative" }}>
              <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height: "auto", display: "block" }}>
                {/* Graph Edges */}
                {graphData.edges.map((edge, idx) => {
                  const src = nodeMap.get(edge.source);
                  const tgt = nodeMap.get(edge.target);
                  if (!src || !tgt) return null;

                  const strokeColor =
                    edge.risk_level === "high" ? "#ef4444" : edge.risk_level === "medium" ? "#f59e0b" : "#10b981";
                  const strokeWidth = Math.max(1.5, Math.min(6, (edge.amount / 50000) * 4));

                  return (
                    <line
                      key={idx}
                      x1={src.x}
                      y1={src.y}
                      x2={tgt.x}
                      y2={tgt.y}
                      stroke={strokeColor}
                      strokeWidth={strokeWidth}
                      strokeOpacity="0.65"
                      strokeDasharray={edge.risk_level === "high" ? "4,4" : undefined}
                    />
                  );
                })}

                {/* Graph Nodes */}
                {positionedNodes.map((node) => {
                  const isSelected = selectedNode?.id === node.id;
                  const isSender = node.type === "sender";
                  const isMule = node.type === "mule" || node.type === "blocked";
                  const fill = isSender ? "#2563eb" : isMule ? "#dc2626" : "#10b981";
                  const radius = isSender ? 26 : isMule ? 20 : 16;

                  return (
                    <g
                      key={node.id}
                      transform={`translate(${node.x}, ${node.y})`}
                      onClick={() => setSelectedNode(node)}
                      style={{ cursor: "pointer" }}
                    >
                      {isSelected && (
                        <circle r={radius + 7} fill="none" stroke="#60a5fa" strokeWidth="2.5" strokeDasharray="3,3" />
                      )}
                      <circle r={radius} fill={fill} stroke="#ffffff" strokeWidth="2" />
                      <text
                        y={radius + 14}
                        textAnchor="middle"
                        fill="#cbd5e1"
                        fontSize="10.5"
                        fontWeight="600"
                        style={{ pointerEvents: "none" }}
                      >
                        {node.label.length > 15 ? node.label.slice(0, 13) + "..." : node.label}
                      </text>
                      <text
                        y="4"
                        textAnchor="middle"
                        fill="#ffffff"
                        fontSize="10"
                        fontWeight="700"
                        style={{ pointerEvents: "none" }}
                      >
                        {isSender ? "SRC" : isMule ? "MULE" : "REC"}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>
          )}

          <div style={{ display: "flex", gap: "1rem", marginTop: "0.85rem", fontSize: "0.8rem", color: "#64748b" }}>
            <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
              <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#2563eb" }} /> Origin
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
              <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#dc2626" }} /> Mule / Blocked
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
              <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: "#10b981" }} /> Clean Receiver
            </span>
          </div>
        </section>

        {/* Right Column: Node Inspector & AI Copilot SAR */}
        <section className="panel">
          <div className="section-heading">
            <p className="eyebrow">Entity Forensics</p>
            <h1>Node Inspector</h1>
          </div>

          {selectedNode ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginBottom: "1.2rem" }}>
              <div
                style={{
                  background: "#f8fafc",
                  border: "1px solid #e2e8f0",
                  borderRadius: "8px",
                  padding: "1rem",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.5rem",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <strong style={{ fontSize: "1rem", color: "#0f172a" }}>{selectedNode.label}</strong>
                  <span
                    style={{
                      fontSize: "0.75rem",
                      fontWeight: 700,
                      padding: "2px 8px",
                      borderRadius: "999px",
                      background: selectedNode.type === "mule" || selectedNode.type === "blocked" ? "#fee2e2" : "#dbeafe",
                      color: selectedNode.type === "mule" || selectedNode.type === "blocked" ? "#dc2626" : "#1e40af",
                    }}
                  >
                    {selectedNode.type.toUpperCase()}
                  </span>
                </div>
                <p style={{ margin: 0, fontSize: "0.85rem", color: "#64748b" }}>
                  <strong>Risk Score:</strong> {selectedNode.risk_score} / 100
                </p>
                <p style={{ margin: 0, fontSize: "0.85rem", color: "#64748b" }}>
                  <strong>Total Audited Volume:</strong> INR {Number(selectedNode.total_amount).toLocaleString("en-IN")}
                </p>
                <p style={{ margin: 0, fontSize: "0.85rem", color: "#64748b" }}>
                  <strong>Transaction Frequency:</strong> {selectedNode.tx_count} events
                </p>
              </div>

              <button
                className="icon-text-btn dark"
                onClick={() => handleGenerateSAR()}
                disabled={sarLoading}
                style={{ width: "100%", justifyContent: "center" }}
              >
                <FileText size={16} />
                {sarLoading ? "Compiling Case..." : "AI Copilot: Generate Regulatory SAR"}
              </button>
            </div>
          ) : (
            <p className="muted-text">Click any node on the graph to inspect its forensic topology.</p>
          )}

          {/* AI Copilot SAR Output */}
          {sarData && (
            <div
              style={{
                background: "#f0fdf4",
                border: "1px solid #bbf7d0",
                borderRadius: "8px",
                padding: "1rem",
                display: "flex",
                flexDirection: "column",
                gap: "0.6rem",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontWeight: 700, fontSize: "0.85rem", color: "#166534" }}>
                  Filing Reference: {sarData.filing_id}
                </span>
                <button
                  className="ghost-btn"
                  onClick={handleCopySAR}
                  style={{ fontSize: "0.78rem", padding: "2px 6px", display: "flex", alignItems: "center", gap: "4px" }}
                >
                  {copied ? <CheckCircle size={14} color="#16a34a" /> : <Copy size={14} />}
                  {copied ? "Copied" : "Copy SAR"}
                </button>
              </div>

              <div style={{ fontSize: "0.82rem", color: "#374151", maxHeight: "190px", overflowY: "auto" }}>
                <p style={{ fontWeight: 600, marginBottom: "4px" }}>Recommended Enforcement:</p>
                <ul style={{ margin: 0, paddingLeft: "1.2rem", fontSize: "0.78rem" }}>
                  {sarData.recommended_actions.map((act, i) => (
                    <li key={i}>{act}</li>
                  ))}
                </ul>
                <p style={{ fontWeight: 600, margin: "8px 0 4px 0" }}>Statutory Violations:</p>
                <ul style={{ margin: 0, paddingLeft: "1.2rem", fontSize: "0.78rem", color: "#dc2626" }}>
                  {sarData.regulatory_violations.map((vio, i) => (
                    <li key={i}>{vio}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
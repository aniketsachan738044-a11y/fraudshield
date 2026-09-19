import { Check, Code2, Copy, Play, Send, ShieldCheck, Terminal, Webhook } from "lucide-react";
import { useState } from "react";

const API_BASE = "http://127.0.0.1:8000/api";

export function DeveloperPortal() {
  const [activeLang, setActiveLang] = useState("curl");
  const [copiedSnippet, setCopiedSnippet] = useState(false);

  // Webhook Simulator State
  const [webhookEvent, setWebhookEvent] = useState("payment.captured");
  const [intentId, setIntentId] = useState("1");
  const [webhookSecret, setWebhookSecret] = useState("default-dev-webhook-secret");
  const [simulating, setSimulating] = useState(false);
  const [simulationResult, setSimulationResult] = useState(null);

  const snippets = {
    curl: `curl -X POST "${API_BASE}/payments/intents" \\
  -H "Content-Type: application/json" \\
  -H "Idempotency-Key: idem_$(date +%s)_$RANDOM" \\
  -d '{
    "amount": 4999.00,
    "currency": "INR",
    "transaction_type": "upi",
    "channel": "mobile_app",
    "receiver_id": "merchant@bank",
    "receiver_age_days": 180,
    "device_trust_score": 0.95
  }'`,
    python: `import requests
import uuid

url = "${API_BASE}/payments/intents"
headers = {
    "Idempotency-Key": f"idem_{uuid.uuid4().hex[:16]}",
    "Content-Type": "application/json"
}
payload = {
    "amount": 4999.00,
    "currency": "INR",
    "transaction_type": "upi",
    "channel": "mobile_app",
    "receiver_id": "merchant@bank",
    "receiver_age_days": 180,
    "device_trust_score": 0.95
}

response = requests.post(url, json=payload, headers=headers)
data = response.json()
print("Risk Score:", data["intent"]["risk_score"])
print("Decision:", data["intent"]["decision"])`,
    javascript: `const idempotencyKey = "idem_" + crypto.randomUUID().slice(0, 16);

const response = await fetch("${API_BASE}/payments/intents", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Idempotency-Key": idempotencyKey
  },
  body: JSON.stringify({
    amount: 4999.00,
    currency: "INR",
    transaction_type: "upi",
    channel: "mobile_app",
    receiver_id: "merchant@bank",
    receiver_age_days: 180,
    device_trust_score: 0.95
  })
});

const data = await response.json();
console.log("Risk Score:", data.intent.risk_score);
console.log("Decision:", data.intent.decision);`,
  };

  function copyCode() {
    navigator.clipboard.writeText(snippets[activeLang]);
    setCopiedSnippet(true);
    setTimeout(() => setCopiedSnippet(false), 2000);
  }

  // Pure JS HMAC-SHA256 calculation for browser
  async function computeHmacSha256(key, message) {
    const enc = new TextEncoder();
    const keyData = enc.encode(key);
    const msgData = enc.encode(message);
    const cryptoKey = await crypto.subtle.importKey(
      "raw",
      keyData,
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"]
    );
    const signature = await crypto.subtle.sign("HMAC", cryptoKey, msgData);
    return Array.from(new Uint8Array(signature))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }

  async function handleSimulateWebhook(e) {
    e.preventDefault();
    setSimulating(true);
    setSimulationResult(null);

    const timestamp = Math.floor(Date.now() / 1000).toString();
    const payloadObj = { event: webhookEvent, intent_id: parseInt(intentId) || 1 };
    const rawBody = JSON.stringify(payloadObj);

    try {
      // Calculate real HMAC-SHA256 signature
      const signMessage = `${timestamp}.${rawBody}`;
      const signature = await computeHmacSha256(webhookSecret, signMessage);

      const res = await fetch(`${API_BASE}/payments/webhook`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Signature": signature,
          "X-Timestamp": timestamp,
        },
        body: rawBody,
      });

      const json = await res.json();
      setSimulationResult({
        status: res.status,
        ok: res.ok,
        signatureComputed: signature,
        timestamp,
        response: json,
      });
    } catch (err) {
      setSimulationResult({
        status: 500,
        ok: false,
        error: err.message,
      });
    } finally {
      setSimulating(false);
    }
  }

  return (
    <div className="two-column-layout">
      {/* Left Column: SDK Quickstart & Code Examples */}
      <section className="panel">
        <div className="section-heading">
          <p className="eyebrow">Integration Guide</p>
          <h1>Developer REST API</h1>
        </div>

        <p className="muted-text" style={{ fontSize: "0.88rem", marginBottom: "1rem" }}>
          Intercept transactions pre-settlement by calling FraudShield before dispatching payment provider calls.
        </p>

        {/* Language Tabs */}
        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem" }}>
          {["curl", "python", "javascript"].map((lang) => (
            <button
              key={lang}
              className={`ghost-btn ${activeLang === lang ? "active" : ""}`}
              style={{
                textTransform: "uppercase",
                fontWeight: 600,
                fontSize: "0.8rem",
                padding: "4px 12px",
                border: activeLang === lang ? "2px solid #2563eb" : "1px solid #cbd5e1",
              }}
              onClick={() => setActiveLang(lang)}
            >
              {lang}
            </button>
          ))}
          <button
            className="icon-text-btn"
            style={{ marginLeft: "auto", fontSize: "0.78rem", padding: "4px 10px" }}
            onClick={copyCode}
          >
            {copiedSnippet ? <Check size={14} color="#16a34a" /> : <Copy size={14} />}
            {copiedSnippet ? "Copied" : "Copy Code"}
          </button>
        </div>

        <pre
          style={{
            background: "#0f172a",
            color: "#e2e8f0",
            padding: "1rem",
            borderRadius: "8px",
            fontSize: "0.82rem",
            overflowX: "auto",
            lineHeight: 1.5,
          }}
        >
          <code>{snippets[activeLang]}</code>
        </pre>
      </section>

      {/* Right Column: Webhook Simulator Playground */}
      <section className="panel">
        <div className="section-heading">
          <p className="eyebrow">Sandbox Testing</p>
          <h1>HMAC Webhook Simulator</h1>
        </div>

        <p className="muted-text" style={{ fontSize: "0.88rem", marginBottom: "1rem" }}>
          Simulate signed gateway callback events and test constant-time HMAC-SHA256 signature verification.
        </p>

        <form
          onSubmit={handleSimulateWebhook}
          style={{
            background: "#f8fafc",
            border: "1px solid #e2e8f0",
            borderRadius: "8px",
            padding: "1rem",
            display: "flex",
            flexDirection: "column",
            gap: "0.85rem",
          }}
        >
          <div>
            <label style={{ fontSize: "0.8rem", fontWeight: 600, color: "#334155", display: "block", marginBottom: "4px" }}>
              Event Type
            </label>
            <select
              value={webhookEvent}
              onChange={(e) => setWebhookEvent(e.target.value)}
              style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
            >
              <option value="payment.captured">payment.captured (Settle Intent)</option>
              <option value="payment.failed">payment.failed (Fail Intent)</option>
            </select>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
            <div>
              <label style={{ fontSize: "0.8rem", fontWeight: 600, color: "#334155", display: "block", marginBottom: "4px" }}>
                Target Payment Intent ID
              </label>
              <input
                type="number"
                min="1"
                value={intentId}
                onChange={(e) => setIntentId(e.target.value)}
                style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
              />
            </div>
            <div>
              <label style={{ fontSize: "0.8rem", fontWeight: 600, color: "#334155", display: "block", marginBottom: "4px" }}>
                HMAC Secret Key
              </label>
              <input
                type="text"
                value={webhookSecret}
                onChange={(e) => setWebhookSecret(e.target.value)}
                style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
              />
            </div>
          </div>

          <button
            type="submit"
            className="icon-text-btn dark"
            disabled={simulating}
            style={{ alignSelf: "flex-start", marginTop: "0.25rem" }}
          >
            <Send size={16} />
            {simulating ? "Signing & Dispatching..." : "Simulate Webhook Delivery"}
          </button>
        </form>

        {/* Live Simulator Response Box */}
        {simulationResult && (
          <div
            style={{
              marginTop: "1.2rem",
              background: simulationResult.ok ? "#f0fdf4" : "#fef2f2",
              border: `1px solid ${simulationResult.ok ? "#bbf7d0" : "#fecaca"}`,
              borderRadius: "8px",
              padding: "1rem",
              fontSize: "0.82rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
              <span style={{ fontWeight: 700, color: simulationResult.ok ? "#166534" : "#dc2626" }}>
                HTTP {simulationResult.status} {simulationResult.ok ? "Verified & Handled" : "Verification Rejected"}
              </span>
              <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Epoch: {simulationResult.timestamp}</span>
            </div>

            {simulationResult.signatureComputed && (
              <p style={{ margin: "4px 0", color: "#475569", wordBreak: "break-all" }}>
                <strong>Computed SHA256:</strong> {simulationResult.signatureComputed.slice(0, 32)}...
              </p>
            )}

            <pre style={{ margin: "6px 0 0 0", padding: "8px", background: "#ffffff", borderRadius: "4px", overflowX: "auto" }}>
              <code>{JSON.stringify(simulationResult.response || simulationResult.error, null, 2)}</code>
            </pre>
          </div>
        )}
      </section>
    </div>
  );
}
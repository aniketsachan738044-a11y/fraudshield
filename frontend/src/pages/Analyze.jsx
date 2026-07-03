import { AlertTriangle, CheckCircle2, CreditCard, ShieldAlert, Sparkles } from "lucide-react";
import { useState } from "react";
import { api } from "../api/client.js";
import { RiskBadge } from "../components/RiskBadge.jsx";
import { ScoreBar } from "../components/ScoreBar.jsx";

const initialForm = {
  amount: 95000,
  transaction_type: "upi",
  channel: "payment_link",
  receiver_id: "new-upi-merchant",
  receiver_age_days: 1,
  hour: 2,
  device_trust_score: 0.22,
  location_mismatch: true,
  is_international: false,
  note: "Urgent payment link received on chat",
};

const presets = [
  {
    label: "Low risk",
    values: {
      amount: 500,
      transaction_type: "upi",
      channel: "mobile_app",
      receiver_id: "known-shop",
      receiver_age_days: 365,
      hour: 14,
      device_trust_score: 0.95,
      location_mismatch: false,
      is_international: false,
      note: "Regular grocery payment",
    },
  },
  {
    label: "Big safe",
    values: {
      amount: 50000,
      transaction_type: "bank_transfer",
      channel: "mobile_app",
      receiver_id: "family-account",
      receiver_age_days: 730,
      hour: 13,
      device_trust_score: 0.98,
      location_mismatch: false,
      is_international: false,
      note: "College fee transfer",
    },
  },
  {
    label: "Scam risk",
    values: initialForm,
  },
];

export function Analyze() {
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setNotice("");

    try {
      const payload = {
        ...form,
        amount: Number(form.amount),
        currency: "INR",
        receiver_age_days: Number(form.receiver_age_days),
        hour: Number(form.hour),
        device_trust_score: Number(form.device_trust_score),
      };
      const idempotencyKey = `intent-${crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`}`;
      const response = await api.createPaymentIntent(payload, idempotencyKey);
      setResult(response);
      setNotice(`Payment intent #${response.intent.id} created with ${response.intent.decision} decision`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSandboxConfirm() {
    setConfirming(true);
    setError("");
    setNotice("");

    try {
      const updatedIntent = await api.confirmPaymentIntent(result.intent.id);
      setResult((current) => ({ ...current, intent: updatedIntent }));
      setNotice(`Sandbox provider approved ${updatedIntent.provider_reference}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setConfirming(false);
    }
  }

  const intent = result?.intent;
  const transaction = intent?.transaction;

  return (
    <div className="page-grid">
      <section className="panel">
        <div className="section-heading">
          <p className="eyebrow">Live analysis</p>
          <h1>Analyze transaction</h1>
        </div>

        <div className="preset-row" aria-label="Transaction presets">
          {presets.map((preset) => (
            <button
              key={preset.label}
              type="button"
              className="preset-btn"
              onClick={() => {
                setForm(preset.values);
                setResult(null);
                setError("");
                setNotice("");
              }}
            >
              <Sparkles size={15} />
              {preset.label}
            </button>
          ))}
        </div>

        <form className="form-grid" onSubmit={handleSubmit}>
          <label>
            Amount
            <input type="number" value={form.amount} onChange={(event) => updateField("amount", event.target.value)} />
          </label>

          <label>
            Type
            <select value={form.transaction_type} onChange={(event) => updateField("transaction_type", event.target.value)}>
              <option value="upi">UPI</option>
              <option value="bank_transfer">Bank transfer</option>
              <option value="card">Card</option>
              <option value="wallet">Wallet</option>
              <option value="atm">ATM</option>
            </select>
          </label>

          <label>
            Channel
            <select value={form.channel} onChange={(event) => updateField("channel", event.target.value)}>
              <option value="mobile_app">Mobile app</option>
              <option value="web">Web</option>
              <option value="qr">QR</option>
              <option value="payment_link">Payment link</option>
              <option value="pos">POS</option>
              <option value="atm">ATM</option>
            </select>
          </label>

          <label>
            Receiver ID
            <input value={form.receiver_id} onChange={(event) => updateField("receiver_id", event.target.value)} />
          </label>

          <label>
            Receiver age days
            <input
              type="number"
              value={form.receiver_age_days}
              onChange={(event) => updateField("receiver_age_days", event.target.value)}
            />
          </label>

          <label>
            Hour
            <input min="0" max="23" type="number" value={form.hour} onChange={(event) => updateField("hour", event.target.value)} />
          </label>

          <label>
            Device trust
            <input
              min="0"
              max="1"
              step="0.01"
              type="number"
              value={form.device_trust_score}
              onChange={(event) => updateField("device_trust_score", event.target.value)}
            />
          </label>

          <label className="check-row">
            <input
              type="checkbox"
              checked={form.location_mismatch}
              onChange={(event) => updateField("location_mismatch", event.target.checked)}
            />
            Location mismatch
          </label>

          <label className="check-row">
            <input
              type="checkbox"
              checked={form.is_international}
              onChange={(event) => updateField("is_international", event.target.checked)}
            />
            International
          </label>

          <label className="full-span">
            Note
            <input value={form.note} onChange={(event) => updateField("note", event.target.value)} />
          </label>

          {error && <p className="error-text full-span">{error}</p>}
          {notice && <p className="success-text full-span">{notice}</p>}

          <button className="primary-btn full-span" disabled={loading}>
            <ShieldAlert size={18} />
            {loading ? "Creating intent..." : "Create payment intent"}
          </button>
        </form>
      </section>

      <section className="panel result-panel">
        <div className="section-heading">
          <p className="eyebrow">Decision</p>
          <h2>Risk result</h2>
        </div>

        {!result ? (
          <div className="empty-state">
            <AlertTriangle size={30} />
            <p>Submit a payment to generate a server-side decision.</p>
          </div>
        ) : (
          <>
            <div className="result-topline">
              <RiskBadge level={transaction.risk_level} />
              <ScoreBar score={transaction.risk_score} />
            </div>

            <div className="recommendation">
              <CheckCircle2 size={19} />
              <strong>{transaction.recommendation}</strong>
              <span>{Math.round(result.confidence * 100)}% confidence</span>
            </div>

            <div className={`payment-decision ${intent.decision}`}>
              <CreditCard size={19} />
              <div>
                <strong>{intent.decision.toUpperCase()} · {intent.status.replaceAll("_", " ")}</strong>
                <span>{intent.decision_reason}</span>
              </div>
            </div>

            {intent.provider_reference && <p className="provider-ref">Provider reference: {intent.provider_reference}</p>}

            {intent.status === "ready_for_provider" && (
              <button className="primary-btn" onClick={handleSandboxConfirm} disabled={confirming}>
                <CreditCard size={18} />
                {confirming ? "Confirming..." : "Sandbox approve"}
              </button>
            )}

            <div className="reason-list">
              {transaction.explanations.map((reason) => (
                <article key={reason.code} className={`reason ${reason.severity}`}>
                  <strong>{reason.title}</strong>
                  <p>{reason.detail}</p>
                </article>
              ))}
            </div>
          </>
        )}
      </section>
    </div>
  );
}

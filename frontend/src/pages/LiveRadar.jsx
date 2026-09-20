import {
  AlertTriangle,
  Coins,
  Flame,
  Globe,
  Pause,
  Play,
  Radar,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Trash2,
  Volume2,
  VolumeX,
  Zap,
} from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { useCurrency } from "../context/CurrencyContext.jsx";
import { COUNTRY_CURRENCY_MAP, formatCurrency, getCurrencyMeta } from "../utils/currency.js";

// Web Audio API Synth for Threat Intercept Chime
function playInterceptSound() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = "sine";
    // Sci-fi descending intercept chime
    osc.frequency.setValueAtTime(880, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(320, ctx.currentTime + 0.18);

    gain.gain.setValueAtTime(0.08, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.18);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start();
    osc.stop(ctx.currentTime + 0.2);
  } catch {
    // AudioContext blocked or not supported
  }
}

// Global Merchants including India (Rupees ₹), US ($), UK (£), Europe (€), Switzerland (CHF), Japan (¥), UAE (AED), Nigeria (₦)
const MERCHANTS = [
  // India (Rupees ₹)
  { name: "Flipkart Retail", category: "E-Commerce", city: "Bengaluru", country: "IN", avg: 4200 },
  { name: "Swiggy Instamart", category: "Quick Commerce", city: "Mumbai", country: "IN", avg: 750 },
  { name: "Zomato Dining", category: "Food Delivery", city: "Delhi", country: "IN", avg: 1450 },
  { name: "Tata Neu Croma", category: "Electronics", city: "Pune", country: "IN", avg: 28500 },
  { name: "Reliance Digital", category: "Retail", city: "Hyderabad", country: "IN", avg: 18200 },
  { name: "Razorpay Gateway", category: "Fintech", city: "Bengaluru", country: "IN", avg: 3600 },

  // United States (USD $)
  { name: "Apple Store", category: "Electronics", city: "Cupertino", country: "US", avg: 850 },
  { name: "Amazon Prime", category: "Retail", city: "Seattle", country: "US", avg: 110 },
  { name: "Steam Games", category: "Gaming", city: "Bellevue", country: "US", avg: 45 },

  // United Kingdom (GBP £)
  { name: "Wise Wire Transfer", category: "Remittance", city: "London", country: "GB", avg: 1800 },
  { name: "Revolut UK", category: "Fintech", city: "London", country: "GB", avg: 620 },

  // Europe (EUR €)
  { name: "Binance Europe SEPA", category: "Crypto", city: "Frankfurt", country: "DE", avg: 3800 },
  { name: "Stripe EU Checkout", category: "SaaS", city: "Dublin", country: "IE", avg: 240 },

  // Switzerland (CHF)
  { name: "Rolex Boutique", category: "Luxury Goods", city: "Geneva", country: "CH", avg: 14500 },

  // Japan (JPY ¥)
  { name: "Sony Shinjuku Center", category: "Electronics", city: "Tokyo", country: "JP", avg: 68000 },

  // UAE (AED)
  { name: "Dubai Mall Luxury", category: "Retail", city: "Dubai", country: "AE", avg: 9800 },

  // Nigeria (NGN ₦)
  { name: "Paystack Nigeria", category: "Fintech", city: "Lagos", country: "NG", avg: 340000 },

  // Singapore (SGD S$)
  { name: "GrabPay Services", category: "Transport/Food", city: "Singapore", country: "SG", avg: 85 },
];

function generateRandomTx() {
  const merchant = MERCHANTS[Math.floor(Math.random() * MERCHANTS.length)];
  const isSuspicious = Math.random() < 0.22;
  const isHighRisk = isSuspicious && Math.random() < 0.45;

  let amount;
  if (isHighRisk) {
    amount = Number((merchant.avg * (Math.random() * 4 + 2.5)).toFixed(2));
  } else if (isSuspicious) {
    amount = Number((merchant.avg * (Math.random() * 1.5 + 1.2)).toFixed(2));
  } else {
    amount = Number((merchant.avg * (Math.random() * 0.8 + 0.4)).toFixed(2));
  }

  // Polar coordinates for radar display (angle 0-360, radius 15-90% based on risk)
  const angle = Math.random() * 360;
  const risk = isHighRisk
    ? Math.floor(Math.random() * 20 + 80)
    : isSuspicious
    ? Math.floor(Math.random() * 30 + 45)
    : Math.floor(Math.random() * 35 + 5);

  const radius = Math.min(88, Math.max(16, (risk / 100) * 80 + (Math.random() * 10 - 5)));
  const currencyMeta = getCurrencyMeta(merchant.country);

  return {
    id: `tx_${Math.random().toString(36).slice(2, 9)}`,
    amount,
    currencyCode: currencyMeta.code,
    currencySymbol: currencyMeta.symbol,
    merchant: merchant.name,
    category: merchant.category,
    city: merchant.city,
    country: merchant.country,
    risk,
    status: risk >= 75 ? "BLOCKED" : risk >= 40 ? "CHALLENGE" : "APPROVED",
    angle,
    radius,
    timestamp: new Date().toLocaleTimeString(),
    latency: Math.floor(Math.random() * 18 + 8),
  };
}

export function LiveRadar() {
  const [active, setActive] = useState(true);
  const [speed, setSpeed] = useState(1400); // interval in ms
  const [audioEnabled, setAudioEnabled] = useState(false);
  const { currency: currencyMode, setCurrency: setCurrencyMode } = useCurrency();
  const [blips, setBlips] = useState([]);
  const [stream, setStream] = useState([]);
  const [selectedTx, setSelectedTx] = useState(null);
  const [attackActive, setAttackActive] = useState(null);

  // HUD Metrics
  const [metrics, setMetrics] = useState({
    tps: 1.4,
    interceptedCount: 22,
    interceptedInr: 3480000, // INR equivalent
    totalScored: 154,
    avgLatency: 12,
  });

  const intervalRef = useRef(null);

  // Add a new transaction into stream and radar
  const pushTransaction = (tx) => {
    // Add to blips (keep last 25 for radar visual clarity)
    setBlips((prev) => [tx, ...prev.slice(0, 24)]);

    // Add to live stream feed (keep last 50)
    setStream((prev) => [tx, ...prev.slice(0, 49)]);

    // Update telemetry
    setMetrics((prev) => {
      const isBlocked = tx.status === "BLOCKED";
      // Convert to INR base for metrics telemetry (~83 INR per USD)
      const meta = getCurrencyMeta(tx.country);
      const usdVal = tx.amount * meta.rateToUsd;
      const inrVal = usdVal * 83.5;

      return {
        ...prev,
        totalScored: prev.totalScored + 1,
        interceptedCount: isBlocked ? prev.interceptedCount + 1 : prev.interceptedCount,
        interceptedInr: isBlocked ? prev.interceptedInr + inrVal : prev.interceptedInr,
        avgLatency: Math.round((prev.avgLatency * 9 + tx.latency) / 10),
      };
    });

    if (tx.status === "BLOCKED" && audioEnabled) {
      playInterceptSound();
    }
  };

  // Regular automated simulated transaction feed
  useEffect(() => {
    if (!active) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      return;
    }

    intervalRef.current = setInterval(() => {
      const tx = generateRandomTx();
      pushTransaction(tx);
    }, speed);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [active, speed, audioEnabled]);

  // Attack Scenario 1: Indian UPI Fast-Smurfing Loop (₹49,999 below reporting limit)
  const triggerUpiSmurfingAttack = async () => {
    if (attackActive) return;
    setAttackActive("UPI Smurfing Loop (India ₹)");

    for (let i = 0; i < 6; i++) {
      await new Promise((resolve) => setTimeout(resolve, 280));
      const tx = {
        id: `upi_smurf_${Math.random().toString(36).slice(2, 7)}`,
        amount: 49999, // Structured just below ₹50k PAN limit
        currencyCode: "INR",
        currencySymbol: "₹",
        merchant: "UPI Rapid Transfer to New VPA",
        category: "UPI Smurfing Mule",
        city: "Mumbai / Pune",
        country: "IN",
        risk: 96,
        status: "BLOCKED",
        angle: 140 + (i * 18),
        radius: 84,
        timestamp: new Date().toLocaleTimeString(),
        latency: 11,
      };
      pushTransaction(tx);
    }

    setTimeout(() => setAttackActive(null), 1200);
  };

  // Attack Scenario 2: Global Card Testing Storm (micro-charges in rotating currencies)
  const triggerCardTestingAttack = async () => {
    if (attackActive) return;
    setAttackActive("Global Card Testing Storm");

    const samples = [
      { country: "IN", amount: 140, merchant: "Razorpay Micro-Check" },
      { country: "US", amount: 2.10, merchant: "Stripe Online Micro-Check" },
      { country: "GB", amount: 1.65, merchant: "Wise Micro-Auth" },
      { country: "DE", amount: 1.95, merchant: "Adyen SEPA Ping" },
      { country: "JP", amount: 280, merchant: "GMO Payment Test" },
    ];

    for (let i = 0; i < 10; i++) {
      await new Promise((resolve) => setTimeout(resolve, 220));
      const s = samples[i % samples.length];
      const meta = getCurrencyMeta(s.country);
      const tx = {
        id: `card_test_${Math.random().toString(36).slice(2, 7)}`,
        amount: s.amount,
        currencyCode: meta.code,
        currencySymbol: meta.symbol,
        merchant: s.merchant,
        category: "Carding Bot Net",
        city: "Rotating Proxy Node",
        country: s.country,
        risk: 94,
        status: "BLOCKED",
        angle: 45 + (i * 14),
        radius: 82,
        timestamp: new Date().toLocaleTimeString(),
        latency: 9,
      };
      pushTransaction(tx);
    }

    setTimeout(() => setAttackActive(null), 1200);
  };

  // Attack Scenario 3: Account Takeover (High-value rapid cashouts)
  const triggerAtoAttack = async () => {
    if (attackActive) return;
    setAttackActive("Account Takeover (ATO Cashout)");

    for (let i = 0; i < 4; i++) {
      await new Promise((resolve) => setTimeout(resolve, 380));
      const tx = {
        id: `ato_spike_${Math.random().toString(36).slice(2, 7)}`,
        amount: 485000, // ₹4.85 Lakhs
        currencyCode: "INR",
        currencySymbol: "₹",
        merchant: "Instant IMPS / Wire Drain",
        category: "ATO Cashout",
        city: "Impossible Travel (Lagos / Mumbai)",
        country: "IN",
        risk: 98,
        status: "BLOCKED",
        angle: 210 + (i * 20),
        radius: 88,
        timestamp: new Date().toLocaleTimeString(),
        latency: 14,
      };
      pushTransaction(tx);
    }

    setTimeout(() => setAttackActive(null), 1200);
  };

  // Display amount formatter considering currency mode
  const renderFormattedAmount = (amount, country) => {
    if (currencyMode === "INR") {
      const meta = getCurrencyMeta(country);
      const inrAmount = (amount * meta.rateToUsd * 83.5);
      return formatCurrency(inrAmount, "IN");
    }
    if (currencyMode === "USD") {
      const meta = getCurrencyMeta(country);
      const usdAmount = (amount * meta.rateToUsd);
      return formatCurrency(usdAmount, "US");
    }
    // Default: native country currency
    return formatCurrency(amount, country);
  };

  const blockRate =
    metrics.totalScored > 0
      ? ((metrics.interceptedCount / metrics.totalScored) * 100).toFixed(1)
      : "0.0";

  return (
    <div className="live-radar-page">
      {/* Top Header & Attack Alert Banner */}
      <div className="radar-header-row">
        <div>
          <div className="radar-title-group">
            <span className="radar-live-badge">
              <span className="live-pulse-dot" /> LIVE
            </span>
            <h1 className="radar-title">Real-Time Threat Radar</h1>
          </div>
          <p className="radar-subtitle">
            Autonomous multi-currency stream scoring (₹ Rupees, $ USD, £ GBP, € EUR, ¥ JPY)
          </p>
        </div>

        <div className="radar-controls-group">
          {/* Currency Display Selector */}
          <div className="currency-selector-wrap" title="Currency display mode">
            <Globe size={14} className="text-muted" />
            <select
              className="radar-speed-select currency-select"
              value={currencyMode}
              onChange={(e) => setCurrencyMode(e.target.value)}
            >
              <option value="native">Currency: Native by Country (₹, $, £, €)</option>
              <option value="INR">Currency: Convert to INR (₹ Rupees)</option>
              <option value="USD">Currency: Convert to USD ($ Dollar)</option>
            </select>
          </div>

          <button
            type="button"
            className={`radar-action-btn ${audioEnabled ? "active" : ""}`}
            onClick={() => setAudioEnabled((v) => !v)}
            title={audioEnabled ? "Mute alert chime" : "Enable intercept audio chime"}
          >
            {audioEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
            <span>{audioEnabled ? "Audio ON" : "Audio OFF"}</span>
          </button>

          <button
            type="button"
            className={`radar-action-btn ${active ? "active" : ""}`}
            onClick={() => setActive((v) => !v)}
          >
            {active ? <Pause size={16} /> : <Play size={16} />}
            <span>{active ? "Pause Stream" : "Resume"}</span>
          </button>

          <select
            className="radar-speed-select"
            value={speed}
            onChange={(e) => setSpeed(Number(e.target.value))}
            title="Stream pacing"
          >
            <option value={2000}>Pacing: Relaxed (2.0s)</option>
            <option value={1400}>Pacing: Normal (1.4s)</option>
            <option value={700}>Pacing: Fast (0.7s)</option>
            <option value={300}>Pacing: Turbo (0.3s)</option>
          </select>
        </div>
      </div>

      {/* Attack Incident Banner */}
      {attackActive && (
        <div className="attack-incident-banner">
          <ShieldAlert size={22} className="alert-banner-icon" />
          <div className="attack-banner-text">
            <strong>SYNTHETIC ATTACK DRILL IN PROGRESS: {attackActive}</strong>
            <span>FraudShield autonomous zero-tolerance rules actively intercepting threats in real-time.</span>
          </div>
        </div>
      )}

      {/* Live HUD Telemetry Cards */}
      <div className="radar-hud-grid">
        <div className="hud-card">
          <span className="hud-label">Stream Throughput</span>
          <strong className="hud-value">
            {active ? (1000 / speed).toFixed(1) : "0.0"} <span className="hud-unit">TPS</span>
          </strong>
          <span className="hud-sub">Transactions / second</span>
        </div>

        <div className="hud-card danger-hud">
          <span className="hud-label">Fraud Intercepted Value</span>
          <strong className="hud-value text-danger">
            {currencyMode === "USD"
              ? `$ ${(metrics.interceptedInr / 83.5).toLocaleString(undefined, { maximumFractionDigits: 0 })}`
              : `₹ ${metrics.interceptedInr.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`}
          </strong>
          <span className="hud-sub">
            {metrics.interceptedCount} malicious attacks neutralized
          </span>
        </div>

        <div className="hud-card">
          <span className="hud-label">Threat Block Rate</span>
          <strong className="hud-value">{blockRate}%</strong>
          <span className="hud-sub">Scored across {metrics.totalScored} intents</span>
        </div>

        <div className="hud-card">
          <span className="hud-label">Scoring Latency</span>
          <strong className="hud-value text-success">
            {metrics.avgLatency} <span className="hud-unit">ms</span>
          </strong>
          <span className="hud-sub">Autonomous SLA p99</span>
        </div>
      </div>

      {/* Main Radar Display & Attack Simulator Console */}
      <div className="radar-layout-grid">
        {/* Left Column: Interactive Radar Canvas */}
        <div className="radar-scanner-panel">
          <div className="panel-topline">
            <div className="flex-center gap-8">
              <Radar size={18} className="text-accent" />
              <h2 className="panel-title">Active 360° Defense Sweep</h2>
            </div>
            <div className="radar-legend">
              <span className="legend-item"><span className="dot dot-green" /> Approved</span>
              <span className="legend-item"><span className="dot dot-amber" /> 2FA Step-up</span>
              <span className="legend-item"><span className="dot dot-red" /> Blocked (&gt;75)</span>
            </div>
          </div>

          <div className="radar-viewport-container">
            <div className="radar-circle-frame">
              {/* Concentric rings */}
              <div className="radar-ring ring-1" />
              <div className="radar-ring ring-2" />
              <div className="radar-ring ring-3" />
              <div className="radar-ring ring-4" />

              {/* Crosshairs */}
              <div className="radar-axis-h" />
              <div className="radar-axis-v" />

              {/* Rotating Sweep Beam */}
              <div className="radar-sweep-beam" />

              {/* Plotted Transaction Blips */}
              {blips.map((blip) => {
                // Convert polar to cartesian (% from center 50%, 50%)
                const rad = (blip.angle * Math.PI) / 180;
                const r = (blip.radius / 100) * 45;
                const left = 50 + r * Math.cos(rad);
                const top = 50 + r * Math.sin(rad);

                const colorClass =
                  blip.status === "BLOCKED"
                    ? "blip-red"
                    : blip.status === "CHALLENGE"
                    ? "blip-amber"
                    : "blip-green";

                return (
                  <button
                    key={blip.id}
                    type="button"
                    className={`radar-blip ${colorClass}`}
                    style={{ left: `${left}%`, top: `${top}%` }}
                    onClick={() => setSelectedTx(blip)}
                    title={`${blip.merchant} (${renderFormattedAmount(blip.amount, blip.country)}) - Risk: ${blip.risk} [${blip.status}]`}
                  >
                    <span className="blip-pulse" />
                  </button>
                );
              })}

              <div className="radar-center-hub">
                <ShieldCheck size={18} />
              </div>
            </div>
          </div>

          {/* Attack Simulator Triggers (Fire Drill Controls) */}
          <div className="attack-drill-box">
            <div className="drill-heading">
              <Flame size={17} className="text-danger" />
              <strong>Synthetic Attack Simulator (Fire Drills)</strong>
            </div>
            <p className="drill-sub">
              Inject synthetic adversarial attack vectors to test FraudShield pre-settlement interception:
            </p>

            <div className="attack-buttons-grid">
              <button
                type="button"
                className="drill-btn drill-btn-amber"
                onClick={triggerUpiSmurfingAttack}
                disabled={Boolean(attackActive)}
              >
                <Coins size={16} />
                <div>
                  <strong>UPI Smurfing Loop (India)</strong>
                  <span>6 rapid ₹49,999 transfers</span>
                </div>
              </button>

              <button
                type="button"
                className="drill-btn drill-btn-red"
                onClick={triggerCardTestingAttack}
                disabled={Boolean(attackActive)}
              >
                <Zap size={16} />
                <div>
                  <strong>Global Card Testing</strong>
                  <span>Micro-charges in ₹, $, £, €</span>
                </div>
              </button>

              <button
                type="button"
                className="drill-btn drill-btn-purple"
                onClick={triggerAtoAttack}
                disabled={Boolean(attackActive)}
              >
                <AlertTriangle size={16} />
                <div>
                  <strong>Account Takeover (ATO)</strong>
                  <span>₹4,85,000 / $9,800 wire drain</span>
                </div>
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Real-Time Stream Terminal */}
        <div className="radar-stream-panel">
          <div className="panel-topline">
            <div className="flex-center gap-8">
              <span className="terminal-dot" />
              <h2 className="panel-title">Interception Stream Log</h2>
              <span className="stream-count-badge">{stream.length} events</span>
            </div>
            <button
              type="button"
              className="ghost-btn icon-btn-sm"
              onClick={() => {
                setStream([]);
                setBlips([]);
              }}
              title="Clear terminal log"
            >
              <Trash2 size={14} />
            </button>
          </div>

          <div className="radar-stream-feed">
            {stream.length === 0 ? (
              <div className="stream-empty-state">
                <Radar size={32} className="empty-radar-icon" />
                <p>Waiting for incoming transaction stream...</p>
                <span>Make sure stream is active above</span>
              </div>
            ) : (
              stream.map((tx) => (
                <div
                  key={tx.id}
                  className={`stream-row ${tx.status === "BLOCKED" ? "row-blocked" : tx.status === "CHALLENGE" ? "row-challenge" : "row-approved"} ${selectedTx?.id === tx.id ? "row-selected" : ""}`}
                  onClick={() => setSelectedTx(tx)}
                >
                  <div className="row-left">
                    <span
                      className={`risk-badge-sm ${tx.status === "BLOCKED" ? "badge-danger" : tx.status === "CHALLENGE" ? "badge-amber" : "badge-success"}`}
                    >
                      {tx.risk}
                    </span>
                    <div>
                      <div className="row-merchant">{tx.merchant}</div>
                      <div className="row-meta">
                        {tx.city}, {tx.country} • {tx.category} • {tx.timestamp}
                      </div>
                    </div>
                  </div>

                  <div className="row-right">
                    <div className="row-amount">{renderFormattedAmount(tx.amount, tx.country)}</div>
                    <span
                      className={`row-status-pill ${tx.status === "BLOCKED" ? "pill-danger" : tx.status === "CHALLENGE" ? "pill-amber" : "pill-success"}`}
                    >
                      {tx.status}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Selected Transaction Inspector Details */}
          {selectedTx && (
            <div className="stream-inspector">
              <div className="inspector-header">
                <strong>Transaction Forensics: {selectedTx.id}</strong>
                <button
                  type="button"
                  className="ghost-btn icon-btn-sm"
                  onClick={() => setSelectedTx(null)}
                >
                  ✕
                </button>
              </div>
              <div className="inspector-grid">
                <div>
                  <span>Merchant:</span> <strong>{selectedTx.merchant}</strong>
                </div>
                <div>
                  <span>Amount:</span>{" "}
                  <strong>{renderFormattedAmount(selectedTx.amount, selectedTx.country)} ({selectedTx.country})</strong>
                </div>
                <div>
                  <span>Origin:</span> <strong>{selectedTx.city}, {selectedTx.country}</strong>
                </div>
                <div>
                  <span>Risk Score:</span>{" "}
                  <strong className={selectedTx.risk >= 75 ? "text-danger" : "text-success"}>
                    {selectedTx.risk} / 100
                  </strong>
                </div>
                <div>
                  <span>Decision:</span> <strong>{selectedTx.status}</strong>
                </div>
                <div>
                  <span>Evaluated Latency:</span> <strong>{selectedTx.latency}ms</strong>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

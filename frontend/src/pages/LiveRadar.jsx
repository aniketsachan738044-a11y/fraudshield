import {
  AlertTriangle,
  Flame,
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
import { api } from "../api/client.js";

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

const MERCHANTS = [
  { name: "Apple Store", category: "Electronics", city: "Cupertino", country: "US", avg: 850 },
  { name: "Amazon Marketplace", category: "Retail", city: "Seattle", country: "US", avg: 110 },
  { name: "Binance On-Ramp", category: "Crypto", city: "Valletta", country: "MT", avg: 4200 },
  { name: "Steam Games", category: "Gaming", city: "Bellevue", country: "US", avg: 45 },
  { name: "Uber Technologies", category: "Transport", city: "San Francisco", country: "US", avg: 28 },
  { name: "Rolex Boutique", category: "Luxury Goods", city: "Geneva", country: "CH", avg: 12500 },
  { name: "Stripe Checkout", category: "SaaS", city: "Dublin", country: "IE", avg: 199 },
  { name: "Wise Wire Transfer", category: "Remittance", city: "London", country: "GB", avg: 3100 },
  { name: "Target Stores", category: "Groceries", city: "Minneapolis", country: "US", avg: 72 },
  { name: "Unknown Proxy Service", category: "VPN/Hosting", city: "Lagos", country: "NG", avg: 940 },
];

function generateRandomTx() {
  const merchant = MERCHANTS[Math.floor(Math.random() * MERCHANTS.length)];
  const isSuspicious = Math.random() < 0.22;
  const isHighRisk = isSuspicious && Math.random() < 0.45;

  let amount;
  if (isHighRisk) {
    amount = Number((Math.random() * 8000 + 2500).toFixed(2));
  } else if (isSuspicious) {
    amount = Number((Math.random() * 1200 + 300).toFixed(2));
  } else {
    amount = Number((Math.random() * merchant.avg * 1.2 + 8).toFixed(2));
  }

  // Polar coordinates for radar display (angle 0-360, radius 15-90% based on risk)
  const angle = Math.random() * 360;
  const risk = isHighRisk ? Math.floor(Math.random() * 20 + 80) : isSuspicious ? Math.floor(Math.random() * 30 + 45) : Math.floor(Math.random() * 35 + 5);

  // Normal radius scaled by risk score: higher risk sits farther out or in critical zone
  const radius = Math.min(88, Math.max(16, (risk / 100) * 80 + (Math.random() * 10 - 5)));

  return {
    id: `tx_${Math.random().toString(36).slice(2, 9)}`,
    amount,
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
  const radarSweepId = useId();
  const [active, setActive] = useState(true);
  const [speed, setSpeed] = useState(1400); // interval in ms
  const [audioEnabled, setAudioEnabled] = useState(false);
  const [blips, setBlips] = useState([]);
  const [stream, setStream] = useState([]);
  const [selectedTx, setSelectedTx] = useState(null);
  const [attackActive, setAttackActive] = useState(null);

  // HUD Metrics
  const [metrics, setMetrics] = useState({
    tps: 1.4,
    interceptedCount: 18,
    interceptedDollars: 42680,
    totalScored: 142,
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
      return {
        ...prev,
        totalScored: prev.totalScored + 1,
        interceptedCount: isBlocked ? prev.interceptedCount + 1 : prev.interceptedCount,
        interceptedDollars: isBlocked ? prev.interceptedDollars + tx.amount : prev.interceptedDollars,
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

  // Attack Scenario: Card Testing Storm (12 micro-charges in 2.5 seconds)
  const triggerCardTestingAttack = async () => {
    if (attackActive) return;
    setAttackActive("Card Testing Storm");

    for (let i = 0; i < 10; i++) {
      await new Promise((resolve) => setTimeout(resolve, 220));
      const amount = Number((Math.random() * 3.5 + 1.2).toFixed(2));
      const tx = {
        id: `card_test_${Math.random().toString(36).slice(2, 7)}`,
        amount,
        merchant: "Stripe Online Micro-Check",
        category: "Card Testing Bot",
        city: "Rotated VPN Proxy",
        country: "RU",
        risk: 94,
        status: "BLOCKED",
        angle: 45 + (i * 12) + (Math.random() * 5),
        radius: 82 + (Math.random() * 6),
        timestamp: new Date().toLocaleTimeString(),
        latency: 9,
      };
      pushTransaction(tx);
    }

    setTimeout(() => setAttackActive(null), 1200);
  };

  // Attack Scenario: Account Takeover (High-value rapid cashouts)
  const triggerAtoAttack = async () => {
    if (attackActive) return;
    setAttackActive("Account Takeover (ATO)");

    for (let i = 0; i < 4; i++) {
      await new Promise((resolve) => setTimeout(resolve, 380));
      const amount = Number((Math.random() * 3000 + 8500).toFixed(2));
      const tx = {
        id: `ato_spike_${Math.random().toString(36).slice(2, 7)}`,
        amount,
        merchant: "Binance Instant Wire Out",
        category: "ATO Cashout",
        city: "Impossible Travel (Lagos)",
        country: "NG",
        risk: 98,
        status: "BLOCKED",
        angle: 210 + (i * 20),
        radius: 86,
        timestamp: new Date().toLocaleTimeString(),
        latency: 14,
      };
      pushTransaction(tx);
    }

    setTimeout(() => setAttackActive(null), 1200);
  };

  // Attack Scenario: Mule Smurfing Dispersal (Coordinated sub-$10k transfers)
  const triggerMuleAttack = async () => {
    if (attackActive) return;
    setAttackActive("Mule Smurfing Ring");

    for (let i = 0; i < 6; i++) {
      await new Promise((resolve) => setTimeout(resolve, 320));
      const amount = Number((9400 + Math.random() * 450).toFixed(2));
      const tx = {
        id: `mule_loop_${Math.random().toString(36).slice(2, 7)}`,
        amount,
        merchant: "Cross-Border P2P Dispersal",
        category: "Mule Structuring",
        city: "Fan-out Shell Account",
        country: "PA",
        risk: 89,
        status: "BLOCKED",
        angle: 120 + (i * 16),
        radius: 78,
        timestamp: new Date().toLocaleTimeString(),
        latency: 11,
      };
      pushTransaction(tx);
    }

    setTimeout(() => setAttackActive(null), 1200);
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
            Autonomous transaction stream scoring & synthetic attack simulation playground
          </p>
        </div>

        <div className="radar-controls-group">
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
          <span className="hud-label">Stream Rate</span>
          <strong className="hud-value">
            {active ? (1000 / speed).toFixed(1) : "0.0"} <span className="hud-unit">TPS</span>
          </strong>
          <span className="hud-sub">Transactions / second</span>
        </div>

        <div className="hud-card danger-hud">
          <span className="hud-label">Fraud Intercepted Value</span>
          <strong className="hud-value text-danger">
            ${metrics.interceptedDollars.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </strong>
          <span className="hud-sub">{metrics.interceptedCount} malicious intents blocked</span>
        </div>

        <div className="hud-card">
          <span className="hud-label">Auto-Block Rate</span>
          <strong className="hud-value">
            {blockRate}%
          </strong>
          <span className="hud-sub">Scored against {metrics.totalScored} intents</span>
        </div>

        <div className="hud-card">
          <span className="hud-label">Engine Latency</span>
          <strong className="hud-value text-success">
            {metrics.avgLatency} <span className="hud-unit">ms</span>
          </strong>
          <span className="hud-sub">Real-time p99 SLA</span>
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
                // scale radius to fit in 0-48%
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
                    title={`${blip.merchant} ($${blip.amount}) - Risk: ${blip.risk} [${blip.status}]`}
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
                className="drill-btn drill-btn-red"
                onClick={triggerCardTestingAttack}
                disabled={Boolean(attackActive)}
              >
                <Zap size={16} />
                <div>
                  <strong>Card Testing Storm</strong>
                  <span>10 rapid $1–$3 micro-charges</span>
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
                  <span>High-velocity $9,800 cashouts</span>
                </div>
              </button>

              <button
                type="button"
                className="drill-btn drill-btn-amber"
                onClick={triggerMuleAttack}
                disabled={Boolean(attackActive)}
              >
                <Sparkles size={16} />
                <div>
                  <strong>Mule Smurfing Ring</strong>
                  <span>Structured sub-$10k dispersal</span>
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
                    <div className="row-amount">${tx.amount.toFixed(2)}</div>
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
                  <span>Amount:</span> <strong>${selectedTx.amount.toFixed(2)}</strong>
                </div>
                <div>
                  <span>Origin:</span> <strong>{selectedTx.city} ({selectedTx.country})</strong>
                </div>
                <div>
                  <span>Risk Score:</span> <strong className={selectedTx.risk >= 75 ? "text-danger" : "text-success"}>{selectedTx.risk} / 100</strong>
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

# FraudShield &mdash; Enterprise AI Fraud Prevention & Risk Decisioning Platform

**FraudShield** is a real-time, hybrid AI and heuristics-driven payment fraud prevention and risk decisioning engine designed to protect modern payment rails (UPI, IMPS, Cards, Net Banking) before funds settle.

Combining unsupervised machine learning (`IsolationForest`) with multi-dimensional deterministic compliance heuristics, FraudShield halts account takeovers, money-mule networks, and authorized push-payment (APP) scams in sub-second latency while keeping checkout frictionless for legitimate customers.

---

## Architecture & System Workflow

```
                        [Client / Merchant Checkout / API Call]
                                           │
                                           ▼
                                [Sliding-Window Limiter]
                             (Redis Cluster / In-Memory Queue)
                                           │
                                           ▼
                           [Context Aggregation Pipeline]
                  (GeoIP Kinematics, 5m Bursts, 1h Velocity, 30d Baseline)
                                           │
                                           ▼
                                 [Hybrid Risk Engine]
                    ┌──────────────────────┴──────────────────────┐
                    ▼                                             ▼
          [Deterministic Rules]                       [IsolationForest ML]
   • Impossible Travel (>800 km/h)               • Multidimensional Unsupervised Anomaly
   • Mule Fan-Out Structuring                    • Feature Scaling & Signal Extraction
   • Counterparty & IP Blocklist                 • Continual Retraining on Feedback
   • Baseline Spending Outliers
                    │                                             │
                    └──────────────────────┬──────────────────────┘
                                           │
                                           ▼
                              [Dynamic Scoring: 0 - 100]
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         ▼                                 ▼                                 ▼
   [0 - 34: LOW RISK]             [35 - 64: MEDIUM RISK]            [65 - 100: HIGH RISK]
         │                                 │                                 │
         ▼                                 ▼                                 ▼
  • Direct Gateway Handoff         • Dynamic Step-Up 2FA Challenge   • Hard Transaction Block
  • Stripe / Razorpay / Sandbox    • SMS (Twilio) / Email (SMTP)     • Fraud Alert Logging
  • Webhook Notification           • User Re-Verification            • HMAC-SHA256 Signed Webhook
```

---

## Core Capabilities

### 1. Hybrid Dual-Layer Decision Engine
- **Unsupervised ML Anomaly Detection**: Powered by scikit-learn's `IsolationForest` with persistent serialization via `joblib`, catching zero-day behavioral outliers across high-dimensional feature vectors.
- **Explainable Fraud Scoring**: Provides human-readable forensic reasons (e.g., `Burst payment pattern`, `Impossible travel velocity`, `Counterparty on security blocklist`) with severity classifications (`low`, `medium`, `high`).

### 2. "Impossible Travel" GeoIP Kinematics
- Calculates instantaneous velocity ($km/h$) using the Haversine great-circle formula between consecutive payment locations.
- Any transaction pair exceeding commercial aviation speeds ($> 800\text{ km/h}$) automatically escalates risk to $\ge 92.0$ with an immediate hard block.

### 3. Mule Account Fan-Out & Structuring Detection
- Sliding-window graph heuristics flag accounts dispersing payments to $\ge 3$ distinct counterparties within a 15-minute window.
- Detects smurfing and money-mule laundering patterns before stolen funds can be layered across multiple dummy accounts.

### 4. Dynamic Risk-Based Step-Up Authentication (2FA / OTP)
- Instead of disrupting every transaction, FraudShield dynamically challenges only medium-risk events ($35 \le \text{score} < 65$).
- Issues a cryptographically hashed 6-digit OTP with a 10-minute TTL, dispatchable via **Twilio SMS**, **SMTP Email**, or the interactive UI sandbox card.

### 5. Multi-Provider Gateway Adapter Pattern
- Extensible `BasePaymentGateway` architecture with pluggable adapters:
  - **Stripe**: Live `PaymentIntent.create` with manual capture workflows.
  - **Razorpay**: Live `client.order.create` and payment capture handoffs.
  - **Sandbox**: Local offline simulation engine for staging and integration tests.
- Gracefully falls back to mock tokens during network outages or if API keys are unconfigured.

### 6. Rule Studio & Counterparty Blocklist Manager
- Web console tab providing live visibility into all engine rules.
- Real-time management interface to blacklist suspicious UPI handles, account IDs, and IP addresses with zero deployment downtime.

### 7. Continuous ML Retraining Pipeline & Feedback Loop
- Fraud analysts can flag transactions directly in the dashboard as confirmed fraud/chargebacks or clean payments (`POST /api/transactions/{id}/feedback`).
- Single-click **"Retrain ML Model"** button (`POST /api/analytics/retrain`) updates the production model artifact incorporating historical audit feedback.

### 8. Executive PDF Compliance Report Export
- Compiles boardroom-ready, audit-compliant PDF risk summaries via `reportlab` (`GET /api/transactions/export.pdf`).
- Includes executive KPI summary cards, risk distributions, and complete forensic transaction ledgers.

### 9. Fintech-Grade Security
- **HMAC-SHA256 Webhooks**: Validates cryptographic signatures with replay attack tolerance checks ($300\text{s}$).
- **Database Idempotency**: Hardened against race conditions and payload mismatch errors (`409 Conflict`).
- **Distributed Redis Rate Limiting**: Sliding-window ZSET log counter with seamless automatic in-memory fallback.

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python 3.12, FastAPI, Uvicorn, SQLAlchemy, Pydantic v2, Alembic, ReportLab |
| **Intelligence** | Scikit-learn (`IsolationForest`), NumPy, Joblib |
| **Frontend** | React 18, Vite, Lucide React, CSS Modern Grid/Flexbox |
| **Databases & Cache** | PostgreSQL 16 (production), SQLite (local dev), Redis (optional rate limit store) |
| **Security** | PyJWT (JOSE), Passlib (Bcrypt), HMAC-SHA256, HTTP-Only Cookies |
| **DevOps & Deploy** | Docker, Docker Compose, Nginx, Pytest, GitHub Actions CI |

---

## Quickstart (Local Development)

### 1. Prerequisites
- Python 3.10+ (or [uv](https://docs.astral.sh/uv/))
- Node.js 18+ and npm

### 2. Backend Setup
```bash
cd backend
# Create environment and install dependencies
uv venv .venv
uv pip install -r requirements.txt

# Start backend with auto-reload
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be live at: **`http://127.0.0.1:8000/docs`**

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Web Application will be live at: **`http://127.0.0.1:5173`**

---

## Docker Compose (Production Deployment)

Run the entire platform (PostgreSQL 16, FastAPI Backend, and Nginx-backed Frontend) with a single command:

```bash
docker-compose up --build -d
```
- **Web App**: `http://localhost:80`
- **Backend API**: `http://localhost:80/api`
- **API Docs**: `http://localhost:80/api/docs`

---

## Running Automated Tests

Run the full backend test suite covering 26 unit and integration test cases:

```bash
cd backend
.venv\Scripts\pytest.exe -v
```

```text
============================= test session starts =============================
platform win32 -- Python 3.12.13, pytest-8.3.4, pluggy-1.6.0
collected 26 items

tests\test_api.py ....................                                   [ 76%]
tests\test_config.py ..                                                  [ 84%]
tests\test_fraud_engine.py ......                                        [100%]

====================== 26 passed, 38 warnings in 15.58s =======================
```

---

## Environment Variables

Configure via `backend/.env`:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `development` | Environment mode (`development` or `production`) |
| `SECRET_KEY` | *(auto)* | JWT cryptographic signing secret |
| `DATABASE_URL` | `sqlite:///./fraudshield.db` | SQLAlchemy database connection URI |
| `REDIS_URL` | `None` | Optional Redis URI for distributed rate limiting |
| `PAYMENT_PROVIDER` | `sandbox` | Active payment gateway (`sandbox`, `stripe`, `razorpay`) |
| `STRIPE_SECRET_KEY` | `None` | Live Stripe API secret key |
| `RAZORPAY_KEY_ID` | `None` | Live Razorpay Key ID |
| `RAZORPAY_KEY_SECRET` | `None` | Live Razorpay Secret |
| `TWILIO_ACCOUNT_SID` | `None` | Twilio Account SID for live SMS 2FA |
| `TWILIO_AUTH_TOKEN` | `None` | Twilio Auth Token |
| `TWILIO_FROM_NUMBER` | `None` | Twilio registered sender number |
| `SMTP_HOST` | `None` | SMTP Host for email 2FA alerts |
| `WEBHOOK_SECRET` | *(auto)* | Shared secret for HMAC-SHA256 webhook signatures |


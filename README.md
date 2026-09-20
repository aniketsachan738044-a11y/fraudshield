# FraudShield &mdash; Enterprise AI Fraud Prevention & Risk Decisioning Platform

<div align="center">

[![Vercel Deployment](https://img.shields.io/badge/Vercel-Live%20Demo-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://fraudshield-zeta.vercel.app)
[![CI Status](https://img.shields.io/badge/GitHub%20Actions-CI%20Passing-22c55e?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/aniketsachan738044-a11y/fraudshield/actions)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8.0-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)
[![PWA](https://img.shields.io/badge/PWA-Ready-5A0FC8?style=for-the-badge&logo=pwa&logoColor=white)](https://fraudshield-zeta.vercel.app)
[![AI](https://img.shields.io/badge/AI%20Copilot-Gemini%20Enabled-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)

**[🚀 Launch Live Web App](https://fraudshield-zeta.vercel.app)** &nbsp; | &nbsp; **[📖 API Documentation (OpenAPI)](http://127.0.0.1:8000/docs)** &nbsp; | &nbsp; **[⚡ Developer Portal](https://fraudshield-zeta.vercel.app/#/developer)**

</div>

---

**FraudShield** is a production-grade, hybrid AI and heuristics-driven payment fraud prevention and risk decisioning platform designed to protect modern payment rails (UPI, Cards, Instant Wires, Net Banking) before funds settle.

Combining unsupervised machine learning (`IsolationForest`) with multi-dimensional deterministic compliance heuristics and graph topology mapping, FraudShield halts account takeovers, money-mule networks, and authorized push-payment (APP) scams in sub-second latency while keeping checkout frictionless for legitimate customers.

---

## 🏛️ Architecture & System Workflow

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
   • Impossible Travel (>800 km/h)               • Multidimensional Anomaly Scoring
   • Mule Fan-Out Structuring                    • Feature Scaling & Signal Extraction
   • Counterparty & IP Blocklist                 • Continual Retraining on Feedback
   • Baseline Spending Outliers                  • Graph Topology Anomaly Ring Detection
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
  • Webhook Notification           • User Re-Verification            • FinCEN SAR Filing Generator
                                                                     • HMAC-SHA256 Signed Webhook
```

---

## 🌟 Key Features & Capabilities

### 1. 🕸️ Interactive Money-Mule Network Graph Visualizer
- **Fund Flow Topology**: Real-time extraction of transaction graphs identifying circular smurfing patterns, rapid fan-in/fan-out hubs, and risk connections.
- **Topology Explorer UI**: Color-coded node risk classification (Normal, Suspicious, High-Risk Mule), cluster-based filtering, and real-time node forensic inspection.
- **AI-Linked Investigation**: Click any node to instantly trigger an AI forensic case investigation and regulatory filing.

### 2. 🤖 AI Fraud Copilot & Automated SAR Generator (FinCEN / FIU)
- **Automated Case Dossier**: Synthesizes account transaction history, counterparty graphs, and heuristic risk triggers into a formal investigative brief (`POST /api/analytics/investigate-case`).
- **Regulatory Filings**: Automatically formats legal **Suspicious Activity Reports (SAR)** with statutory citations (e.g. BSA Structuring 31 U.S.C. § 5324, PMLA 2002 Section 12).
- **Google Gemini Integration**: Optional connection to Google Gemini (`gemini-1.5-flash`) for prosecutorial narrative generation, with built-in deterministic fallback.

### 3. ⚡ Developer Integration Portal & Webhook Playground
- **Multi-Language SDK Snippets**: Copy-paste integration examples in **cURL**, **Python** (`requests`), and **JavaScript** (`fetch`) for `/api/transactions/score`.
- **HMAC-SHA256 Webhook Simulator**: Interactive browser-native playground simulating signed webhook event delivery using Web Crypto API, demonstrating constant-time signature verification (`hmac.compare_digest`).

### 4. 🚀 Impossible Travel GeoIP Kinematics
- Calculates velocity ($km/h$) using the Haversine great-circle formula between consecutive payment locations.
- Any transaction pair exceeding commercial aviation speeds ($> 800\text{ km/h}$) automatically escalates risk to $\ge 92.0$ with an immediate hard block.

### 5. 🔄 Continuous ML Retraining Pipeline & Feedback Loop
- Fraud analysts flag transactions directly in the dashboard as confirmed fraud/chargebacks or false positives (`POST /api/transactions/{id}/feedback`).
- Single-click **"Retrain ML Model"** button (`POST /api/analytics/retrain`) updates the serialized `artifacts/fraud_model.joblib` model artifact on-the-fly.

### 6. 💳 Resilient Payment Gateway Architecture
- Pluggable gateway adapters for **Stripe** (live `PaymentIntent` manual capture), **Razorpay** (order capture), and an offline **Sandbox**.
- Seamless fallback to simulated tokens during network degradation, ensuring zero downtime.

### 7. 📱 Progressive Web App (PWA) Mobile Ready
- Installable on iOS and Android home screens with standalone display mode, custom app icons, and offline shell caching.

---

## 🛠️ Tech Stack & Libraries

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 19, Vite 8, Tailwind CSS, Lucide Icons, Recharts, SVG Canvas |
| **Backend API** | Python 3.12, FastAPI 0.115, Uvicorn, Pydantic v2 Settings |
| **Database & ORM** | SQLAlchemy 2.0, SQLite (Local/Dev), PostgreSQL (Production Ready), Alembic |
| **Machine Learning** | Scikit-learn (`IsolationForest`), NumPy, Joblib |
| **Security & Auth** | Python-Jose (JWT), Passlib / Bcrypt, HMAC-SHA256 Constant-Time Verification |
| **Integrations** | Stripe SDK, Razorpay SDK, Twilio REST API, SMTP Email, Redis Cache, Google Gemini |
| **DevOps & Deploy** | Vercel (Frontend Edge), Render (Backend Python), Docker, GitHub Actions CI |

---

## 🧪 Verification & Automated Testing

FraudShield maintains a comprehensive automated test suite with **100% pass rate**:

```bash
cd backend
.\.venv\Scripts\pytest.exe
```

```text
============================= test session starts =============================
platform win32 -- Python 3.12.13, pytest-8.3.4, pluggy-1.6.0
collected 28 items

tests\test_api.py ....................                                   [ 71%]
tests\test_config.py ..                                                  [ 78%]
tests\test_fraud_engine.py ......                                        [100%]

====================== 28 passed, 43 warnings in 20.83s =======================
```

---

## 🚀 Quick Start (Local Setup)

### 1. Clone & Run Backend
```bash
git clone https://github.com/aniketsachan738044-a11y/fraudshield.git
cd fraudshield/backend

# Create virtual environment & install dependencies
python -m venv .venv
.\.venv\Scripts\activate  # On Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

# Start FastAPI server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 2. Run Frontend
```bash
cd ../frontend
npm install
npm run dev
```
Frontend App: [http://127.0.0.1:5173](http://127.0.0.1:5173)

---

## 📄 License
Distributed under the MIT License. See `LICENSE` for details.

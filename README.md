# FraudShield

FraudShield is a full-stack fraud detection dashboard for UPI and banking-style transactions. It scores transaction risk, explains why a payment is suspicious, stores user history, exports CSV reports, and shows analytics suitable for a portfolio demo.

## Highlights

- JWT authentication with hashed passwords and HTTP-only session cookies
- SQLite persistence through SQLAlchemy
- Explainable fraud scoring with Isolation Forest plus rule-based reasons
- Server-side payment intents with idempotency keys
- Allow/review/block payment policy before provider handoff
- Audit logs for auth and payment actions
- Demo presets for low-risk, large trusted, and suspicious transactions
- Dashboard with search, risk filters, CSV export, and clear-history reset
- Analytics summary, risk breakdown, and demo model metrics
- Login rate limiting
- Responsive React UI
- Backend tests and GitHub Actions CI
- Render and Vercel deployment config

## Tech Stack

Backend: FastAPI, SQLAlchemy, SQLite, scikit-learn, python-jose, passlib, pytest

Frontend: React, Vite, lucide-react, CSS

Deployment: Render backend, Vercel frontend, GitHub Actions CI

## Project Structure

```text
fraudshield/
  backend/
    app/
      routes/
      services/
      main.py
      models.py
      schemas.py
      security.py
    tests/
    requirements.txt
    render.yaml
  frontend/
    src/
      api/
      auth/
      components/
      pages/
    package.json
    vercel.json
  .github/workflows/ci.yml
  DEPLOY.md
```

## Local Setup

Backend:

```bash
cd backend
copy .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

Open `http://localhost:5173`.

## Tests

```bash
cd backend
pytest
```

## Demo Flow

1. Register a new user.
2. Create a payment intent from the prefilled risky transaction.
3. Read the allow/review/block decision and risk reasons.
4. Try the Low risk preset and use Sandbox approve.
5. Open Dashboard to see saved history.
6. Export the CSV report.
7. Open Analytics to show risk distribution and model metrics.

## Important Note

This is a portfolio-grade fraud detection and sandbox payment-risk system, not a live money movement product. The model metrics use synthetic labeled examples because real financial fraud datasets are sensitive and difficult to access.

For real money, keep FraudShield behind a licensed payment gateway, replace SQLite with managed PostgreSQL, complete legal/compliance review, add OTP/MFA, webhook signature verification, monitoring, incident response, and independent security testing.

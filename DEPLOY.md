# FraudShield Deployment

This project is split into a FastAPI backend and a Vite React frontend.

## 1. Push to GitHub

```bash
git init
git add .
git commit -m "Build FraudShield"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/fraudshield.git
git push -u origin main
```

## 2. Deploy Backend on Render

1. Open Render and create a new Web Service.
2. Connect the GitHub repo.
3. Set Root Directory to `backend`.
4. Set Build Command:

```bash
pip install -r requirements.txt
```

5. Set Start Command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

6. Add environment variables:

```text
ENVIRONMENT=production
SECRET_KEY=<generate a long random value>
DATABASE_URL=sqlite:///./fraudshield.db
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=none
PAYMENT_PROVIDER=sandbox
FRONTEND_URL=https://your-frontend.vercel.app
ALLOWED_ORIGINS=https://your-frontend.vercel.app
```

Copy the Render backend URL after deployment.

## 3. Deploy Frontend on Vercel

1. Import the same GitHub repo into Vercel.
2. Set Root Directory to `frontend`.
3. Add environment variable:

```text
VITE_API_URL=https://your-render-backend.onrender.com/api
```

4. Deploy.

## 4. Final Check

Open the Vercel URL and test:

- Register a new account.
- Create a high-risk payment intent and confirm it is blocked.
- Create a Low risk payment intent and use Sandbox approve.
- Open Dashboard and confirm it was saved.
- Download the CSV report.
- Open Analytics and confirm metrics load.

Render free tier can sleep after inactivity, so the first request can take around 30 seconds.

## Real Money Boundary

The deployed app must stay in `PAYMENT_PROVIDER=sandbox` until you connect a licensed payment gateway account. Do not collect card numbers, UPI PINs, bank passwords, or real customer financial data in this app.

Before live money, move `DATABASE_URL` to managed PostgreSQL, add signed provider webhooks, OTP/MFA for risky payments, audit-log retention, monitoring alerts, and a legal/compliance review for your region.

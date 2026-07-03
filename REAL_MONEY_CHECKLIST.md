# Real Money Readiness Checklist

FraudShield is now structured like a payment-risk layer, but it should stay in sandbox mode until every item below is handled.

## Required Before Live Payments

- Use a licensed payment gateway or bank partner for all money movement.
- Keep `PAYMENT_PROVIDER=sandbox` until provider credentials, contracts, and compliance review are complete.
- Replace SQLite with managed PostgreSQL and automated backups.
- Store secrets in the hosting provider secret manager.
- Verify all provider webhooks with signatures and timestamps.
- Use idempotency keys for every payment creation request.
- Add OTP/MFA for login, high-value payments, new receivers, and risky devices.
- Add role-based admin access and manual review queues.
- Log every login, payment intent, provider callback, approval, block, refund, and admin action.
- Add alerting for fraud spikes, webhook failures, brute-force login attempts, and payment errors.
- Run dependency scanning, static analysis, and an independent penetration test.
- Write refund, dispute, incident response, and data-retention procedures.

## Never Collect Directly

- UPI PINs
- Card numbers or CVV
- Net banking passwords
- Aadhaar/PAN unless your legal basis and storage controls are reviewed
- Real customer financial data in demo environments

## Current Safe Mode

The current implementation creates server-side payment intents, applies a risk policy, records audit logs, and allows only low-risk intents to be `approved_sandbox`. No real money is moved.

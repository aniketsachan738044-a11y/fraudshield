from uuid import uuid4
import os
from pathlib import Path

test_db_path = Path(__file__).parent / "test_fraudshield.db"
if test_db_path.exists():
    test_db_path.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"
os.environ["SECRET_KEY"] = "test-secret-key-for-fraudshield"

from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app


init_db()
client = TestClient(app)


def register_user() -> str:
    email = f"test-{uuid4()}@example.com"
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "strong-password-123", "full_name": "Test User"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_auth_required_for_transactions() -> None:
    response = client.get("/api/transactions")
    assert response.status_code == 401


def test_analyze_transaction_and_export_csv() -> None:
    token = register_user()
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/transactions/analyze",
        headers=headers,
        json={
            "amount": 82000,
            "transaction_type": "upi",
            "channel": "payment_link",
            "receiver_id": "fresh-receiver",
            "receiver_age_days": 2,
            "hour": 1,
            "device_trust_score": 0.2,
            "location_mismatch": True,
            "is_international": False,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["transaction"]["risk_level"] == "high"
    assert body["transaction"]["explanations"]

    csv_response = client.get("/api/transactions/export.csv", headers=headers)
    assert csv_response.status_code == 200
    assert "fraudshield-report.csv" in csv_response.headers["content-disposition"]
    assert "fresh-receiver" in csv_response.text

    clear_response = client.delete("/api/transactions", headers=headers)
    assert clear_response.status_code == 204

    list_response = client.get("/api/transactions", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_cookie_session_can_read_profile() -> None:
    email = f"cookie-{uuid4()}@example.com"
    session_client = TestClient(app)

    register_response = session_client.post(
        "/api/auth/register",
        json={"email": email, "password": "strong-password-123", "full_name": "Cookie User"},
    )

    assert register_response.status_code == 201
    assert "fraudshield_session" in session_client.cookies

    me_response = session_client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == email


def test_payment_intent_is_idempotent_and_can_be_sandbox_confirmed() -> None:
    token = register_user()
    idempotency_key = f"pay-{uuid4()}"
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": idempotency_key}
    payload = {
        "amount": 500,
        "currency": "INR",
        "transaction_type": "upi",
        "channel": "mobile_app",
        "receiver_id": "known-shop",
        "receiver_age_days": 365,
        "hour": 14,
        "device_trust_score": 0.95,
        "location_mismatch": False,
        "is_international": False,
    }

    response = client.post("/api/payments/intents", headers=headers, json=payload)
    replay_response = client.post("/api/payments/intents", headers=headers, json=payload)

    assert response.status_code == 201
    assert replay_response.status_code == 201
    body = response.json()
    replay_body = replay_response.json()
    assert body["intent"]["id"] == replay_body["intent"]["id"]
    assert body["intent"]["decision"] == "allow"
    assert body["intent"]["status"] == "ready_for_provider"

    confirm_response = client.post(
        f"/api/payments/intents/{body['intent']['id']}/sandbox-confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "approved_sandbox"
    assert confirm_response.json()["provider_reference"].startswith("sandbox_")


def test_high_risk_payment_intent_is_blocked_before_provider() -> None:
    token = register_user()
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": f"pay-{uuid4()}"}

    response = client.post(
        "/api/payments/intents",
        headers=headers,
        json={
            "amount": 95000,
            "currency": "INR",
            "transaction_type": "upi",
            "channel": "payment_link",
            "receiver_id": "new-upi-merchant",
            "receiver_age_days": 1,
            "hour": 2,
            "device_trust_score": 0.22,
            "location_mismatch": True,
            "is_international": False,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["intent"]["decision"] == "block"
    assert body["intent"]["status"] == "blocked"

    confirm_response = client.post(
        f"/api/payments/intents/{body['intent']['id']}/sandbox-confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirm_response.status_code == 409


def test_idempotency_mismatch_returns_409() -> None:
    token = register_user()
    idempotency_key = f"pay-{uuid4()}"
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": idempotency_key}
    base_payload = {
        "amount": 1000,
        "currency": "INR",
        "transaction_type": "upi",
        "channel": "mobile_app",
        "receiver_id": "receiver-a",
        "receiver_age_days": 100,
        "hour": 12,
        "device_trust_score": 0.9,
    }

    # First request succeeds
    res1 = client.post("/api/payments/intents", headers=headers, json=base_payload)
    assert res1.status_code == 201

    # Replay with different amount
    res2 = client.post("/api/payments/intents", headers=headers, json={**base_payload, "amount": 9999})
    assert res2.status_code == 409
    assert "mismatched transaction parameters" in res2.json()["detail"]


def test_clear_transactions_creates_audit_log_and_cleans_intents() -> None:
    token = register_user()
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": f"pay-{uuid4()}"}

    # Create intent & transaction
    client.post(
        "/api/payments/intents",
        headers=headers,
        json={
            "amount": 200,
            "currency": "INR",
            "transaction_type": "upi",
            "channel": "mobile_app",
            "receiver_id": "test-shop",
            "receiver_age_days": 200,
            "device_trust_score": 0.9,
        },
    )

    # Clear
    clear_res = client.delete("/api/transactions", headers={"Authorization": f"Bearer {token}"})
    assert clear_res.status_code == 204

    # Transactions should now be empty
    list_res = client.get("/api/transactions", headers={"Authorization": f"Bearer {token}"})
    assert list_res.status_code == 200
    assert list_res.json() == []


def test_analyze_without_explicit_hour() -> None:
    token = register_user()
    headers = {"Authorization": f"Bearer {token}"}

    # Omit hour field
    res = client.post(
        "/api/transactions/analyze",
        headers=headers,
        json={
            "amount": 1500,
            "transaction_type": "upi",
            "channel": "mobile_app",
            "receiver_id": "auto-hour-shop",
            "receiver_age_days": 100,
            "device_trust_score": 0.85,
        },
    )
    assert res.status_code == 201
    assert 0 <= res.json()["transaction"]["hour"] <= 23


def test_rate_limiter_proxy_ip() -> None:
    from app.rate_limit import SlidingWindowRateLimiter

    limiter = SlidingWindowRateLimiter(limit=3, window_seconds=60)
    limiter.check("ip-1")
    limiter.check("ip-1")
    limiter.check("ip-1")

    # 4th hit raises 429
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        limiter.check("ip-1")
    assert exc_info.value.status_code == 429

    # Different IP is not affected
    limiter.check("ip-2")


def test_step_up_otp_request_and_verification() -> None:
    token = register_user()
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": f"pay-{uuid4()}"}

    # Medium risk payment that requires review
    create_res = client.post(
        "/api/payments/intents",
        headers=headers,
        json={
            "amount": 25000,
            "currency": "INR",
            "transaction_type": "upi",
            "channel": "payment_link",
            "receiver_id": "review-merchant",
            "receiver_age_days": 20,
            "hour": 14,
            "device_trust_score": 0.8,
            "location_mismatch": False,
            "is_international": False,
        },
    )
    assert create_res.status_code == 201
    intent_data = create_res.json()["intent"]
    assert intent_data["status"] == "requires_review"

    # Request OTP
    otp_res = client.post(
        f"/api/payments/intents/{intent_data['id']}/request-otp",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert otp_res.status_code == 200
    demo_otp = otp_res.json()["demo_otp"]
    assert demo_otp is not None

    # Invalid OTP attempt
    bad_verify = client.post(
        f"/api/payments/intents/{intent_data['id']}/verify-otp",
        headers={"Authorization": f"Bearer {token}"},
        json={"otp": "000000"},
    )
    assert bad_verify.status_code == 400

    # Valid OTP verification
    good_verify = client.post(
        f"/api/payments/intents/{intent_data['id']}/verify-otp",
        headers={"Authorization": f"Bearer {token}"},
        json={"otp": demo_otp},
    )
    assert good_verify.status_code == 200
    assert good_verify.json()["status"] == "approved_step_up"
    assert good_verify.json()["provider_reference"].startswith("stepup_")


def test_webhook_hmac_signature_verification() -> None:
    import hashlib
    import hmac
    import json
    import time
    from app.config import get_settings

    token = register_user()
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": f"pay-{uuid4()}"}

    create_res = client.post(
        "/api/payments/intents",
        headers=headers,
        json={
            "amount": 300,
            "currency": "INR",
            "transaction_type": "upi",
            "channel": "mobile_app",
            "receiver_id": "webhook-shop",
            "receiver_age_days": 100,
            "hour": 12,
            "device_trust_score": 0.95,
        },
    )
    intent_id = create_res.json()["intent"]["id"]

    # Reject missing headers
    res_no_headers = client.post("/api/payments/webhook", json={"event": "payment.captured"})
    assert res_no_headers.status_code == 401

    # Prepare signed payload
    secret = get_settings().webhook_secret or "default-dev-webhook-secret"
    payload_dict = {"event": "payment.captured", "intent_id": intent_id}
    raw_body = json.dumps(payload_dict).encode("utf-8")
    timestamp = str(int(time.time()))

    sig = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}.".encode("utf-8") + raw_body,
        hashlib.sha256,
    ).hexdigest()

    # Reject invalid signature
    res_bad_sig = client.post(
        "/api/payments/webhook",
        headers={"X-Signature": "invalid-sig", "X-Timestamp": timestamp, "Content-Type": "application/json"},
        content=raw_body,
    )
    assert res_bad_sig.status_code == 401

    # Accept valid signature
    res_valid = client.post(
        "/api/payments/webhook",
        headers={"X-Signature": sig, "X-Timestamp": timestamp, "Content-Type": "application/json"},
        content=raw_body,
    )
    assert res_valid.status_code == 200

    # Verify intent status transitioned to settled
    intents = client.get("/api/payments/intents", headers={"Authorization": f"Bearer {token}"}).json()
    matched = [i for i in intents if i["id"] == intent_id][0]
    assert matched["status"] == "settled"


def test_export_pdf_report() -> None:
    token = register_user()
    headers = {"Authorization": f"Bearer {token}"}

    # Add a transaction first
    client.post(
        "/api/transactions/analyze",
        headers=headers,
        json={
            "amount": 2500,
            "transaction_type": "upi",
            "channel": "mobile_app",
            "receiver_id": "merchant-pdf",
            "receiver_age_days": 180,
            "hour": 14,
            "device_trust_score": 0.95,
        },
    )

    response = client.get("/api/transactions/export.pdf", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 500


def test_blocklist_crud_and_intent_enforcement() -> None:
    token = register_user()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Add blocklist entry
    blocked_receiver = f"scammer-{uuid4().hex[:6]}@upi"
    create_res = client.post(
        "/api/rules/blocklist",
        headers=headers,
        json={
            "entry_type": "receiver_id",
            "value": blocked_receiver,
            "reason": "Known mule syndicate account",
        },
    )
    assert create_res.status_code == 201
    entry_id = create_res.json()["id"]

    # 2. List blocklist
    list_res = client.get("/api/rules/blocklist", headers=headers)
    assert list_res.status_code == 200
    entries = list_res.json()
    assert any(e["value"] == blocked_receiver for e in entries)

    # 3. Create payment intent to blocked receiver -> must be blocked
    intent_res = client.post(
        "/api/payments/intents",
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": f"test-idem-key-{uuid4().hex}"},
        json={
            "amount": 500,
            "currency": "INR",
            "transaction_type": "upi",
            "channel": "mobile_app",
            "receiver_id": blocked_receiver,
            "receiver_age_days": 120,
            "hour": 15,
            "device_trust_score": 0.95,
        },
    )
    assert intent_res.status_code == 201
    data = intent_res.json()
    assert data["intent"]["status"] == "blocked"
    assert data["intent"]["decision"] == "block"
    assert data["intent"]["risk_score"] == 100.0
    assert any(exp["code"] == "blocklist_match" for exp in data["intent"]["transaction"]["explanations"])

    # 4. Delete entry
    del_res = client.delete(f"/api/rules/blocklist/{entry_id}", headers=headers)
    assert del_res.status_code == 204


def test_impossible_travel_detection() -> None:
    token = register_user()
    headers = {"Authorization": f"Bearer {token}"}

    # First transaction from Mumbai
    res1 = client.post(
        "/api/transactions/analyze",
        headers=headers,
        json={
            "amount": 1000,
            "transaction_type": "upi",
            "channel": "mobile_app",
            "receiver_id": "vendor-1",
            "receiver_age_days": 180,
            "device_trust_score": 0.95,
            "simulated_city": "Mumbai",
        },
    )
    assert res1.status_code == 201
    assert res1.json()["transaction"]["location_city"] == "Mumbai"

    # Immediate second transaction from London (~7,200 km away within seconds)
    res2 = client.post(
        "/api/transactions/analyze",
        headers=headers,
        json={
            "amount": 1200,
            "transaction_type": "upi",
            "channel": "mobile_app",
            "receiver_id": "vendor-2",
            "receiver_age_days": 180,
            "device_trust_score": 0.95,
            "simulated_city": "London",
        },
    )
    assert res2.status_code == 201
    data = res2.json()
    assert data["transaction"]["location_city"] == "London"
    codes = [exp["code"] for exp in data["transaction"]["explanations"]]
    assert "impossible_travel" in codes
    assert data["transaction"]["risk_score"] >= 92.0
    assert data["transaction"]["risk_level"] == "high"


def test_mule_fanout_structuring_detection() -> None:
    token = register_user()
    headers = {"Authorization": f"Bearer {token}"}

    # Send rapid transactions to 3 distinct receivers
    for i in range(3):
        client.post(
            "/api/transactions/analyze",
            headers=headers,
            json={
                "amount": 4900,
                "transaction_type": "upi",
                "channel": "mobile_app",
                "receiver_id": f"mule-rec-{i}",
                "receiver_age_days": 100,
                "device_trust_score": 0.9,
            },
        )

    # 4th transaction to another receiver within the 15-minute window
    res4 = client.post(
        "/api/transactions/analyze",
        headers=headers,
        json={
            "amount": 4950,
            "transaction_type": "upi",
            "channel": "mobile_app",
            "receiver_id": "mule-rec-target",
            "receiver_age_days": 100,
            "device_trust_score": 0.9,
        },
    )
    assert res4.status_code == 201
    codes = [exp["code"] for exp in res4.json()["transaction"]["explanations"]]
    assert "mule_fanout_structuring" in codes
    assert res4.json()["transaction"]["risk_level"] == "high"


def test_transaction_feedback_and_model_retrain() -> None:
    token = register_user()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a transaction
    tx_res = client.post(
        "/api/transactions/analyze",
        headers=headers,
        json={
            "amount": 7500,
            "transaction_type": "upi",
            "channel": "mobile_app",
            "receiver_id": "test-merchant-retrain",
            "receiver_age_days": 180,
            "device_trust_score": 0.88,
        },
    )
    assert tx_res.status_code == 201
    tx_id = tx_res.json()["transaction"]["id"]

    # 2. Submit chargeback feedback
    fb_res = client.post(
        f"/api/transactions/{tx_id}/feedback",
        headers=headers,
        json={"is_fraud": True, "note": "Customer reported fraudulent unauthorized charge"},
    )
    assert fb_res.status_code == 200
    assert fb_res.json()["is_fraud_confirmed"] is True
    assert fb_res.json()["feedback_note"] == "Customer reported fraudulent unauthorized charge"

    # 3. Retrain model incorporating confirmed fraud
    retrain_res = client.post("/api/analytics/retrain", headers=headers)
    assert retrain_res.status_code == 200
    data = retrain_res.json()
    assert data["status"] == "success"
    assert data["trained_samples"] > 1000
    assert 0 <= data["accuracy"] <= 1.0


def test_gateway_adapters_and_fallbacks() -> None:
    from app.services.gateway import RazorpayPaymentGateway, StripePaymentGateway, get_payment_gateway

    # Stripe fallback
    stripe_gw = StripePaymentGateway(api_key=None)
    intent = stripe_gw.create_intent(100.0, "INR", "ref-1")
    assert intent["provider"] == "stripe"
    assert intent["provider_reference"].startswith("pi_mock_")
    cap = stripe_gw.capture_intent(intent["provider_reference"], 100.0)
    assert cap["status"] == "succeeded"

    # Razorpay fallback
    razorpay_gw = RazorpayPaymentGateway(key_id=None, key_secret=None)
    order = razorpay_gw.create_intent(250.0, "INR", "ref-2")
    assert order["provider"] == "razorpay"
    assert order["provider_reference"].startswith("order_mock_")
    rcap = razorpay_gw.capture_intent(order["provider_reference"], 250.0)
    assert rcap["status"] == "captured"

    # Factory resolver
    assert get_payment_gateway("stripe").__class__ == StripePaymentGateway
    assert get_payment_gateway("razorpay").__class__ == RazorpayPaymentGateway


def test_notifications_dispatcher_and_geoip() -> None:
    from app.services.geoip import resolve_ip_location
    from app.services.notifications import dispatch_step_up_otp

    # Dispatcher sandbox fallback
    res = dispatch_step_up_otp("test@example.com", "123456", channel="email")
    assert res["status"] in {"delivered", "skipped"}

    # GeoIP resolution
    city, lat, lon = resolve_ip_location("104.28.1.1")
    assert city == "London"
    assert lat != 0 and lon != 0

    # Local fallback
    d_city, _, _ = resolve_ip_location("127.0.0.1")
    assert d_city == "Delhi"


def test_network_graph_api() -> None:
    token = register_user()
    headers = {"Authorization": f"Bearer {token}"}

    # Create transactions to different counterparties
    client.post(
        "/api/transactions/analyze",
        headers=headers,
        json={
            "amount": 3500,
            "transaction_type": "upi",
            "channel": "mobile_app",
            "receiver_id": "graph-vendor-clean",
            "receiver_age_days": 200,
            "device_trust_score": 0.95,
        },
    )
    client.post(
        "/api/transactions/analyze",
        headers=headers,
        json={
            "amount": 89000,
            "transaction_type": "upi",
            "channel": "payment_link",
            "receiver_id": "graph-mule-suspect",
            "receiver_age_days": 1,
            "device_trust_score": 0.15,
        },
    )

    response = client.get("/api/analytics/network-graph", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data and "edges" in data
    assert len(data["nodes"]) >= 3  # sender + 2 receivers
    assert len(data["edges"]) >= 2
    assert any(n["type"] == "sender" for n in data["nodes"])
    assert any(n["type"] == "mule" for n in data["nodes"])


def test_ai_case_investigator_and_sar_generation() -> None:
    token = register_user()
    headers = {"Authorization": f"Bearer {token}"}

    # Add a high-risk transaction
    tx_res = client.post(
        "/api/transactions/analyze",
        headers=headers,
        json={
            "amount": 99000,
            "transaction_type": "upi",
            "channel": "payment_link",
            "receiver_id": "suspicious-syndicate@upi",
            "receiver_age_days": 1,
            "device_trust_score": 0.1,
            "location_mismatch": True,
        },
    )
    tx_id = tx_res.json()["transaction"]["id"]

    # Generate SAR report
    sar_res = client.post(
        "/api/analytics/investigate-case",
        headers=headers,
        json={"transaction_id": tx_id},
    )
    assert sar_res.status_code == 200
    sar = sar_res.json()
    assert sar["filing_id"].startswith("SAR-IND-")
    assert sar["risk_score"] >= 65.0
    assert len(sar["forensic_timeline"]) >= 2
    assert len(sar["regulatory_violations"]) >= 1
    assert len(sar["recommended_actions"]) >= 1
    assert "SUSPICIOUS ACTIVITY REPORT" in sar["formal_sar_narrative"]



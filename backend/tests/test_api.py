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

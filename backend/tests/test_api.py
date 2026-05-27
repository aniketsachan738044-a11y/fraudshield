from uuid import uuid4
import os
from pathlib import Path

os.environ["DATABASE_URL"] = f"sqlite:///{Path(__file__).parent / 'test_fraudshield.db'}"
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

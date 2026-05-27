from app.schemas import TransactionCreate
from app.services.fraud_engine import fraud_engine


def test_high_risk_transaction_receives_explanation() -> None:
    tx = TransactionCreate(
        amount=95000,
        transaction_type="upi",
        channel="payment_link",
        receiver_id="new-upi-handle",
        receiver_age_days=1,
        hour=2,
        device_trust_score=0.18,
        location_mismatch=True,
    )

    result = fraud_engine.analyze(tx)

    assert result.risk_level == "high"
    assert result.risk_score >= 65
    assert len(result.explanations) >= 3
    assert result.recommendation == "Block and verify with the customer"


def test_low_risk_transaction_is_allowed() -> None:
    tx = TransactionCreate(
        amount=650,
        transaction_type="upi",
        channel="mobile_app",
        receiver_id="known-shop",
        receiver_age_days=300,
        hour=14,
        device_trust_score=0.94,
    )

    result = fraud_engine.analyze(tx)

    assert result.risk_level == "low"
    assert result.risk_score < 35
    assert result.recommendation == "Allow transaction"


def test_demo_metrics_are_available() -> None:
    metrics = fraud_engine.evaluate_demo_model()

    assert 0 <= metrics.accuracy <= 1
    assert 0 <= metrics.precision <= 1
    assert 0 <= metrics.recall <= 1
    assert len(metrics.confusion_matrix) == 2


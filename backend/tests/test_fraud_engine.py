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


def test_velocity_and_spending_spike_rules() -> None:
    from app.schemas import UserTransactionContext

    tx = TransactionCreate(
        amount=12000,
        transaction_type="upi",
        channel="mobile_app",
        receiver_id="new-vendor",
        receiver_age_days=60,
        hour=14,
        device_trust_score=0.9,
    )

    # Baseline without context
    base_result = fraud_engine.analyze(tx)

    # With high velocity and spending spike relative to historical 1,000 average
    context = UserTransactionContext(
        tx_count_last_hour=6,
        tx_count_last_5m=3,
        avg_user_amount=1000.0,
        is_new_receiver_for_user=True,
    )
    flagged_result = fraud_engine.analyze(tx, context=context)

    codes = [exp.code for exp in flagged_result.explanations]
    assert "high_velocity_1h" in codes
    assert "burst_activity" in codes
    assert "spending_spike" in codes
    assert flagged_result.risk_score > base_result.risk_score


def test_server_hour_auto_resolution() -> None:
    tx = TransactionCreate(
        amount=500,
        transaction_type="upi",
        channel="mobile_app",
        receiver_id="test-receiver",
        receiver_age_days=100,
        hour=None,  # Not provided by client
    )
    result = fraud_engine.analyze(tx)
    assert 0 <= result.resolved_hour <= 23


def test_model_joblib_persistence(tmp_path) -> None:
    from app.services.fraud_engine import FraudEngine

    model_file = tmp_path / "test_model.joblib"
    engine1 = FraudEngine(artifact_path=model_file)
    assert model_file.exists()

    engine2 = FraudEngine(artifact_path=model_file)
    assert engine2.model is not None


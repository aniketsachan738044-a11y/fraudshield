from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from random import Random

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score

from app.config import get_settings
from app.schemas import FraudReason, ModelMetrics, RetrainResponse, TransactionCreate, UserTransactionContext


TYPE_RISK = {
    "upi": 8,
    "bank_transfer": 12,
    "card": 10,
    "wallet": 7,
    "atm": 14,
}

CHANNEL_RISK = {
    "mobile_app": 6,
    "web": 10,
    "qr": 16,
    "payment_link": 20,
    "pos": 8,
    "atm": 14,
}


@dataclass(frozen=True)
class FraudResult:
    risk_score: float
    risk_level: str
    recommendation: str
    explanations: list[FraudReason]
    confidence: float
    resolved_hour: int = 12


class FraudEngine:
    def __init__(self, artifact_path: str | Path | None = None) -> None:
        settings = get_settings()
        target_path = Path(artifact_path or settings.model_artifact_path)
        self.artifact_path = target_path

        if target_path.exists():
            try:
                self.model = joblib.load(target_path)
                return
            except Exception:
                pass

        self.model = IsolationForest(n_estimators=160, contamination=0.08, random_state=42)
        self.model.fit(self._training_matrix())
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(self.model, target_path)
        except Exception:
            pass

    def analyze(self, tx: TransactionCreate, context: UserTransactionContext | None = None) -> FraudResult:
        resolved_hour = tx.hour if tx.hour is not None else datetime.now(timezone.utc).hour
        feature_row = np.array([self._features(tx, resolved_hour)])
        isolation_signal = float(-self.model.decision_function(feature_row)[0])
        model_points = max(0.0, min(22.0, (isolation_signal + 0.05) * 95))

        rule_points, reasons = self._rule_score(tx, resolved_hour, context)
        score = round(max(0.0, min(100.0, rule_points + model_points)), 1)
        level = self._risk_level(score)

        if not reasons:
            reasons.append(
                FraudReason(
                    code="normal_pattern",
                    title="Pattern looks normal",
                    detail="Amount, timing, device trust, and receiver profile are within expected ranges.",
                    severity="low",
                )
            )

        recommendation = {
            "low": "Allow transaction",
            "medium": "Review before approval",
            "high": "Block and verify with the customer",
        }[level]

        confidence = round(min(0.94, 0.64 + len(reasons) * 0.045 + score / 420), 2)
        return FraudResult(score, level, recommendation, reasons, confidence, resolved_hour)

    def explanations_to_json(self, explanations: list[FraudReason]) -> str:
        return json.dumps([reason.model_dump() for reason in explanations])

    def explanations_from_json(self, value: str) -> list[FraudReason]:
        return [FraudReason(**item) for item in json.loads(value)]

    def evaluate_demo_model(self) -> ModelMetrics:
        rng = Random(11)
        samples: list[TransactionCreate] = []
        labels: list[int] = []

        for _ in range(420):
            samples.append(self._fake_transaction(rng, fraudulent=False))
            labels.append(0)
        for _ in range(180):
            samples.append(self._fake_transaction(rng, fraudulent=True))
            labels.append(1)

        predictions = [1 if self.analyze(tx).risk_score >= 65 else 0 for tx in samples]
        return ModelMetrics(
            accuracy=round(float(accuracy_score(labels, predictions)), 3),
            precision=round(float(precision_score(labels, predictions, zero_division=0)), 3),
            recall=round(float(recall_score(labels, predictions, zero_division=0)), 3),
            f1_score=round(float(f1_score(labels, predictions, zero_division=0)), 3),
            confusion_matrix=confusion_matrix(labels, predictions).tolist(),
            note="Demo metrics are computed on labeled synthetic fraud patterns, not bank production data.",
        )

    def retrain_with_feedback(self, feedback_transactions: list) -> RetrainResponse:
        rng = Random(42)
        rows = [self._features(self._fake_transaction(rng, fraudulent=False)) for _ in range(1600)]
        rows += [self._features(self._fake_transaction(rng, fraudulent=True)) for _ in range(200)]

        for tx in feedback_transactions:
            tx_create = TransactionCreate(
                amount=tx.amount,
                transaction_type=tx.transaction_type,
                channel=tx.channel,
                receiver_id=tx.receiver_id,
                receiver_age_days=tx.receiver_age_days,
                hour=tx.hour,
                device_trust_score=tx.device_trust_score,
                location_mismatch=tx.location_mismatch,
                is_international=tx.is_international,
            )
            feat = self._features(tx_create, tx.hour)
            weight = 6 if getattr(tx, "is_fraud_confirmed", False) else 3
            for _ in range(weight):
                rows.append(feat)

        matrix = np.array(rows)
        self.model = IsolationForest(n_estimators=180, contamination=0.08, random_state=42)
        self.model.fit(matrix)

        if self.artifact_path:
            try:
                self.artifact_path.parent.mkdir(parents=True, exist_ok=True)
                joblib.dump(self.model, self.artifact_path)
            except Exception:
                pass

        eval_metrics = self.evaluate_demo_model()
        return RetrainResponse(
            status="success",
            model_type="IsolationForest (Online Adaptive)",
            trained_samples=len(rows),
            accuracy=eval_metrics.accuracy,
            precision=eval_metrics.precision,
            recall=eval_metrics.recall,
            f1_score=eval_metrics.f1_score,
            message=f"Model successfully retrained on {len(rows)} samples incorporating {len(feedback_transactions)} confirmed cases.",
        )

    def _training_matrix(self) -> np.ndarray:
        rng = Random(7)
        rows = [self._features(self._fake_transaction(rng, fraudulent=False)) for _ in range(1800)]
        rows += [self._features(self._fake_transaction(rng, fraudulent=True)) for _ in range(220)]
        return np.array(rows)

    def _fake_transaction(self, rng: Random, fraudulent: bool) -> TransactionCreate:
        if fraudulent:
            amount = rng.choice([rng.uniform(25000, 180000), rng.uniform(5000, 60000)])
            hour = rng.choice([0, 1, 2, 3, 4, 23, rng.randint(5, 22)])
            receiver_age_days = rng.choice([0, 1, 2, 3, 5, rng.randint(6, 20)])
            device_trust = rng.uniform(0.05, 0.45)
            channel = rng.choice(["qr", "payment_link", "web", "atm"])
            tx_type = rng.choice(["upi", "bank_transfer", "wallet", "atm"])
            location_mismatch = rng.random() < 0.68
            international = rng.random() < 0.24
        else:
            amount = rng.lognormvariate(7.25, 0.85)
            hour = min(23, max(0, int(rng.normalvariate(14, 4))))
            receiver_age_days = rng.randint(25, 900)
            device_trust = rng.uniform(0.62, 0.99)
            channel = rng.choice(["mobile_app", "pos", "web", "qr"])
            tx_type = rng.choice(["upi", "card", "wallet", "bank_transfer"])
            location_mismatch = rng.random() < 0.05
            international = rng.random() < 0.015

        return TransactionCreate(
            amount=round(amount, 2),
            transaction_type=tx_type,
            channel=channel,
            receiver_id=f"receiver-{rng.randint(1000, 9999)}",
            receiver_age_days=receiver_age_days,
            hour=hour,
            device_trust_score=round(device_trust, 2),
            location_mismatch=location_mismatch,
            is_international=international,
        )

    def _features(self, tx: TransactionCreate, resolved_hour: int | None = None) -> list[float]:
        hour = resolved_hour if resolved_hour is not None else (tx.hour if tx.hour is not None else 12)
        return [
            math.log1p(tx.amount),
            hour / 23,
            TYPE_RISK[tx.transaction_type] / 20,
            CHANNEL_RISK[tx.channel] / 20,
            min(tx.receiver_age_days, 365) / 365,
            tx.device_trust_score,
            1.0 if tx.location_mismatch else 0.0,
            1.0 if tx.is_international else 0.0,
        ]

    def _rule_score(
        self,
        tx: TransactionCreate,
        resolved_hour: int,
        context: UserTransactionContext | None = None,
    ) -> tuple[float, list[FraudReason]]:
        points = 0.0
        reasons: list[FraudReason] = []

        if tx.amount >= 75000:
            points += 25
            reasons.append(
                FraudReason(
                    code="very_high_amount",
                    title="Very high transaction amount",
                    detail="The amount is much higher than a typical retail payment.",
                    severity="high",
                )
            )
        elif tx.amount >= 20000:
            points += 13
            reasons.append(
                FraudReason(
                    code="high_amount",
                    title="High transaction amount",
                    detail="The amount is elevated and deserves extra review.",
                    severity="medium",
                )
            )

        if resolved_hour <= 5 or resolved_hour >= 23:
            points += 13
            reasons.append(
                FraudReason(
                    code="unusual_hour",
                    title="Unusual transaction time",
                    detail="Fraud attempts often happen late at night or early morning.",
                    severity="medium",
                )
            )

        if tx.receiver_age_days <= 3:
            points += 18
            reasons.append(
                FraudReason(
                    code="new_receiver",
                    title="New receiver profile",
                    detail="The receiver was created very recently.",
                    severity="high",
                )
            )
        elif tx.receiver_age_days <= 14:
            points += 10
            reasons.append(
                FraudReason(
                    code="young_receiver",
                    title="Young receiver profile",
                    detail="The receiver has limited history.",
                    severity="medium",
                )
            )

        if tx.device_trust_score <= 0.3:
            points += 18
            reasons.append(
                FraudReason(
                    code="low_device_trust",
                    title="Low device trust",
                    detail="The device fingerprint looks unfamiliar or risky.",
                    severity="high",
                )
            )
        elif tx.device_trust_score <= 0.55:
            points += 9
            reasons.append(
                FraudReason(
                    code="medium_device_trust",
                    title="Reduced device trust",
                    detail="The device is not fully trusted yet.",
                    severity="medium",
                )
            )

        if tx.location_mismatch:
            points += 14
            reasons.append(
                FraudReason(
                    code="location_mismatch",
                    title="Location mismatch",
                    detail="The transaction location differs from the user's normal pattern.",
                    severity="medium",
                )
            )

        if tx.is_international:
            points += 11
            reasons.append(
                FraudReason(
                    code="international_transfer",
                    title="International transaction",
                    detail="Cross-border transactions carry additional fraud risk.",
                    severity="medium",
                )
            )

        if tx.channel in {"payment_link", "qr"}:
            points += 8
            reasons.append(
                FraudReason(
                    code="risky_channel",
                    title="Higher-risk payment channel",
                    detail="Payment links and QR flows are commonly used in social-engineering scams.",
                    severity="medium",
                )
            )

        # Context-aware velocity & behavioral anomaly checks
        if context:
            if context.tx_count_last_hour >= 5:
                points += 20
                reasons.append(
                    FraudReason(
                        code="high_velocity_1h",
                        title="High transaction velocity",
                        detail=f"High frequency: {context.tx_count_last_hour} transactions initiated within the last hour.",
                        severity="high",
                    )
                )
            elif context.tx_count_last_hour >= 3:
                points += 10
                reasons.append(
                    FraudReason(
                        code="elevated_velocity_1h",
                        title="Elevated transaction frequency",
                        detail=f"Elevated frequency: {context.tx_count_last_hour} transactions initiated within the last hour.",
                        severity="medium",
                    )
                )

            if context.tx_count_last_5m >= 3:
                points += 15
                reasons.append(
                    FraudReason(
                        code="burst_activity",
                        title="Rapid burst payment pattern",
                        detail=f"Burst activity: {context.tx_count_last_5m} payments attempted within a 5-minute window.",
                        severity="high",
                    )
                )

            if context.avg_user_amount and context.avg_user_amount > 0:
                ratio = tx.amount / context.avg_user_amount
                if ratio >= 4.0 and tx.amount >= 5000:
                    points += 18
                    reasons.append(
                        FraudReason(
                            code="spending_spike",
                            title="Abnormal spending spike",
                            detail=f"Amount is {ratio:.1f}x higher than this account's historical average (Rs {context.avg_user_amount:,.0f}).",
                            severity="high",
                        )
                    )
                elif ratio >= 2.5 and tx.amount >= 2500:
                    points += 9
                    reasons.append(
                        FraudReason(
                            code="moderate_spending_spike",
                            title="Above-average payment amount",
                            detail=f"Amount is {ratio:.1f}x higher than this account's historical average (Rs {context.avg_user_amount:,.0f}).",
                            severity="medium",
                        )
                    )

            if context.is_blocked_counterparty:
                return 100.0, [
                    FraudReason(
                        code="blocklist_match",
                        title="Counterparty on security blocklist",
                        detail="The recipient UPI ID or client origin is present on the security blocklist.",
                        severity="high",
                    )
                ]

            if context.impossible_travel_speed_kmh is not None:
                points = max(points + 45.0, 92.0)
                reasons.append(
                    FraudReason(
                        code="impossible_travel",
                        title="Impossible travel velocity detected",
                        detail=(
                            f"Location velocity between consecutive transactions was {context.impossible_travel_speed_kmh:.0f} km/h "
                            f"(from {context.prev_city or 'previous location'} to {context.current_city or 'current location'}), "
                            "exceeding commercial flight speeds."
                        ),
                        severity="high",
                    )
                )

            if context.mule_distinct_receivers_15m >= 3:
                points = max(points + 40.0, 88.0)
                reasons.append(
                    FraudReason(
                        code="mule_fanout_structuring",
                        title="Mule fan-out structuring pattern",
                        detail=f"Structuring anomaly: Sent payments to {context.mule_distinct_receivers_15m} distinct new counterparties within 15 minutes.",
                        severity="high",
                    )
                )

            if context.is_new_receiver_for_user and tx.amount >= 15000:
                points += 10
                reasons.append(
                    FraudReason(
                        code="new_counterparty",
                        title="Transfer to new counterparty",
                        detail="High-value transfer to a receiver not previously transacted with on this account.",
                        severity="medium",
                    )
                )

        points += TYPE_RISK[tx.transaction_type] * 0.25
        points += CHANNEL_RISK[tx.channel] * 0.2
        return points, reasons

    def _risk_level(self, score: float) -> str:
        if score >= 65:
            return "high"
        if score >= 35:
            return "medium"
        return "low"


fraud_engine = FraudEngine()

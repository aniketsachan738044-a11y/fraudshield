from re import fullmatch
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import PaymentIntent, Transaction, User
from app.schemas import PaymentIntentCreate, PaymentIntentRead, PaymentIntentResponse, TransactionRead
from app.security import get_current_user
from app.services.audit import write_audit_log
from app.services.fraud_engine import fraud_engine


router = APIRouter(prefix="/payments", tags=["payments"])


def normalize_idempotency_key(value: str | None) -> str:
    key = (value or "").strip()
    if not fullmatch(r"[A-Za-z0-9._:-]{16,160}", key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key header must be 16-160 URL-safe characters.",
        )
    return key


def payment_policy(risk_level: str, risk_score: float, amount: float) -> tuple[str, str, str]:
    if risk_level == "high" or risk_score >= 70:
        return "blocked", "block", "Blocked before provider handoff because fraud risk is high."
    if risk_level == "medium" or risk_score >= 40 or amount >= 200_000:
        return "requires_review", "review", "Manual review required before provider handoff."
    return "ready_for_provider", "allow", "Low-risk payment can be sent to the configured provider."


def serialize_transaction(transaction: Transaction) -> TransactionRead:
    return TransactionRead(
        id=transaction.id,
        amount=transaction.amount,
        transaction_type=transaction.transaction_type,
        channel=transaction.channel,
        receiver_id=transaction.receiver_id,
        receiver_age_days=transaction.receiver_age_days,
        hour=transaction.hour,
        device_trust_score=transaction.device_trust_score,
        location_mismatch=transaction.location_mismatch,
        is_international=transaction.is_international,
        note=transaction.note,
        risk_score=transaction.risk_score,
        risk_level=transaction.risk_level,
        recommendation=transaction.recommendation,
        explanations=fraud_engine.explanations_from_json(transaction.explanation_json),
        created_at=transaction.created_at,
    )


def serialize_payment_intent(intent: PaymentIntent) -> PaymentIntentRead:
    return PaymentIntentRead(
        id=intent.id,
        transaction_id=intent.transaction_id,
        idempotency_key=intent.idempotency_key,
        provider=intent.provider,
        provider_reference=intent.provider_reference,
        status=intent.status,
        amount=intent.amount,
        currency=intent.currency,
        receiver_id=intent.receiver_id,
        risk_score=intent.risk_score,
        risk_level=intent.risk_level,
        confidence=intent.confidence,
        decision=intent.decision,
        decision_reason=intent.decision_reason,
        created_at=intent.created_at,
        updated_at=intent.updated_at,
        transaction=serialize_transaction(intent.transaction),
    )


@router.post("/intents", response_model=PaymentIntentResponse, status_code=status.HTTP_201_CREATED)
def create_payment_intent(
    payload: PaymentIntentCreate,
    request: Request,
    idempotency_key_header: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentIntentResponse:
    idempotency_key = normalize_idempotency_key(idempotency_key_header)
    existing = (
        db.query(PaymentIntent)
        .filter(PaymentIntent.user_id == current_user.id, PaymentIntent.idempotency_key == idempotency_key)
        .first()
    )
    if existing:
        write_audit_log(db, current_user, "payments.intent_replayed", "success", request, {"intent_id": existing.id})
        return PaymentIntentResponse(intent=serialize_payment_intent(existing), confidence=existing.confidence)

    result = fraud_engine.analyze(payload)
    status_value, decision, decision_reason = payment_policy(result.risk_level, result.risk_score, payload.amount)

    transaction = Transaction(
        user_id=current_user.id,
        amount=payload.amount,
        transaction_type=payload.transaction_type,
        channel=payload.channel,
        receiver_id=payload.receiver_id,
        receiver_age_days=payload.receiver_age_days,
        hour=payload.hour,
        device_trust_score=payload.device_trust_score,
        location_mismatch=payload.location_mismatch,
        is_international=payload.is_international,
        note=payload.note,
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        recommendation=result.recommendation,
        explanation_json=fraud_engine.explanations_to_json(result.explanations),
    )
    db.add(transaction)
    db.flush()

    intent = PaymentIntent(
        user_id=current_user.id,
        transaction_id=transaction.id,
        idempotency_key=idempotency_key,
        provider=get_settings().payment_provider,
        status=status_value,
        amount=payload.amount,
        currency=payload.currency,
        receiver_id=payload.receiver_id,
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        confidence=result.confidence,
        decision=decision,
        decision_reason=decision_reason,
    )
    db.add(intent)
    db.commit()
    db.refresh(intent)
    write_audit_log(
        db,
        current_user,
        "payments.intent_created",
        intent.status,
        request,
        {"intent_id": intent.id, "decision": intent.decision, "risk_score": intent.risk_score},
    )
    return PaymentIntentResponse(intent=serialize_payment_intent(intent), confidence=result.confidence)


@router.get("/intents", response_model=list[PaymentIntentRead])
def list_payment_intents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PaymentIntentRead]:
    intents = (
        db.query(PaymentIntent)
        .filter(PaymentIntent.user_id == current_user.id)
        .order_by(PaymentIntent.created_at.desc())
        .limit(100)
        .all()
    )
    return [serialize_payment_intent(intent) for intent in intents]


@router.post("/intents/{intent_id}/sandbox-confirm", response_model=PaymentIntentRead)
def sandbox_confirm_payment_intent(
    intent_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentIntentRead:
    intent = (
        db.query(PaymentIntent)
        .filter(PaymentIntent.id == intent_id, PaymentIntent.user_id == current_user.id)
        .first()
    )
    if intent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment intent not found")
    if intent.status != "ready_for_provider":
        write_audit_log(db, current_user, "payments.sandbox_confirm", "rejected", request, {"intent_id": intent.id})
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only low-risk ready intents can be sandbox-confirmed")

    intent.status = "approved_sandbox"
    intent.provider_reference = f"sandbox_{uuid4().hex[:16]}"
    db.commit()
    db.refresh(intent)
    write_audit_log(
        db,
        current_user,
        "payments.sandbox_confirm",
        "success",
        request,
        {"intent_id": intent.id, "provider_reference": intent.provider_reference},
    )
    return serialize_payment_intent(intent)

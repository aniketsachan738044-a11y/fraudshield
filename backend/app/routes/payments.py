import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from re import fullmatch
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import BlocklistEntry, PaymentIntent, Transaction, User
from app.rate_limit import get_client_ip
from app.schemas import (
    OTPRequestResponse,
    OTPVerifyRequest,
    PaymentIntentCreate,
    PaymentIntentRead,
    PaymentIntentResponse,
    TransactionRead,
    UserTransactionContext,
    WebhookPayload,
)
from app.security import get_current_user, pwd_context
from app.services.audit import write_audit_log
from app.services.fraud_engine import fraud_engine
from app.services.gateway import get_payment_gateway
from app.services.geoip import haversine_distance_km, resolve_ip_location
from app.services.notifications import dispatch_step_up_otp


router = APIRouter(prefix="/payments", tags=["payments"])


def normalize_idempotency_key(value: str | None) -> str:
    key = (value or "").strip()
    if not fullmatch(r"[A-Za-z0-9._:-]{16,160}", key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key header must be 16-160 URL-safe characters.",
        )
    return key


def compute_user_context(
    db: Session,
    user_id: int,
    receiver_id: str,
    request: Request | None = None,
    simulated_city: str | None = None,
) -> tuple[UserTransactionContext, str, float, float]:
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    five_minutes_ago = now - timedelta(minutes=5)
    fifteen_minutes_ago = now - timedelta(minutes=15)
    thirty_days_ago = now - timedelta(days=30)

    client_ip = get_client_ip(request) if request else "127.0.0.1"
    current_city, current_lat, current_lon = resolve_ip_location(client_ip, city_override=simulated_city)

    # 1. Blocklist check
    is_blocked = (
        db.query(BlocklistEntry)
        .filter(
            (BlocklistEntry.user_id == user_id) | (BlocklistEntry.user_id.is_(None)),
            (
                (BlocklistEntry.entry_type == "receiver_id") & (BlocklistEntry.value == receiver_id)
                | (BlocklistEntry.entry_type == "ip_address") & (BlocklistEntry.value == client_ip)
            ),
        )
        .first()
        is not None
    )

    # 2. Velocity counts
    tx_count_1h = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.user_id == user_id, Transaction.created_at >= one_hour_ago)
        .scalar()
        or 0
    )
    tx_count_5m = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.user_id == user_id, Transaction.created_at >= five_minutes_ago)
        .scalar()
        or 0
    )
    mule_count = (
        db.query(func.count(func.distinct(Transaction.receiver_id)))
        .filter(Transaction.user_id == user_id, Transaction.created_at >= fifteen_minutes_ago)
        .scalar()
        or 0
    )
    avg_amount = (
        db.query(func.avg(Transaction.amount))
        .filter(Transaction.user_id == user_id, Transaction.created_at >= thirty_days_ago)
        .scalar()
    )
    prior_tx_count = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.user_id == user_id, Transaction.receiver_id == receiver_id)
        .scalar()
        or 0
    )

    # 3. Impossible travel check
    last_tx = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id, Transaction.location_lat.isnot(None))
        .order_by(Transaction.created_at.desc())
        .first()
    )

    impossible_speed = None
    prev_city = None
    if last_tx and last_tx.location_lat and last_tx.location_lon and last_tx.created_at:
        tx_created = last_tx.created_at
        if tx_created.tzinfo is None:
            tx_created = tx_created.replace(tzinfo=timezone.utc)
        elapsed_seconds = max(1.0, (now - tx_created).total_seconds())
        elapsed_hours = elapsed_seconds / 3600.0
        dist_km = haversine_distance_km(last_tx.location_lat, last_tx.location_lon, current_lat, current_lon)
        if dist_km >= 120.0 and elapsed_hours <= 6.0:
            speed = dist_km / elapsed_hours
            if speed > 800.0:
                impossible_speed = speed
                prev_city = last_tx.location_city

    context = UserTransactionContext(
        tx_count_last_hour=tx_count_1h,
        tx_count_last_5m=tx_count_5m,
        avg_user_amount=float(avg_amount) if avg_amount is not None else None,
        is_new_receiver_for_user=(prior_tx_count == 0),
        mule_distinct_receivers_15m=mule_count,
        is_blocked_counterparty=is_blocked,
        impossible_travel_speed_kmh=impossible_speed,
        prev_city=prev_city,
        current_city=current_city,
    )
    return context, current_city, current_lat, current_lon


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
        location_city=transaction.location_city,
        location_lat=transaction.location_lat,
        location_lon=transaction.location_lon,
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
        if (
            abs(existing.amount - payload.amount) > 0.001
            or existing.currency != payload.currency
            or existing.receiver_id != payload.receiver_id
        ):
            write_audit_log(
                db,
                current_user,
                "payments.intent_mismatch",
                "rejected",
                request,
                {"intent_id": existing.id, "idempotency_key": idempotency_key},
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key replayed with mismatched transaction parameters.",
            )

        write_audit_log(db, current_user, "payments.intent_replayed", "success", request, {"intent_id": existing.id})
        return PaymentIntentResponse(intent=serialize_payment_intent(existing), confidence=existing.confidence)

    context, city, lat, lon = compute_user_context(
        db,
        current_user.id,
        payload.receiver_id,
        request=request,
        simulated_city=payload.simulated_city,
    )
    result = fraud_engine.analyze(payload, context=context)
    status_value, decision, decision_reason = payment_policy(result.risk_level, result.risk_score, payload.amount)

    transaction = Transaction(
        user_id=current_user.id,
        amount=payload.amount,
        transaction_type=payload.transaction_type,
        channel=payload.channel,
        receiver_id=payload.receiver_id,
        receiver_age_days=payload.receiver_age_days,
        hour=result.resolved_hour,
        device_trust_score=payload.device_trust_score,
        location_mismatch=payload.location_mismatch,
        is_international=payload.is_international,
        location_city=city,
        location_lat=lat,
        location_lon=lon,
        note=payload.note,
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        recommendation=result.recommendation,
        explanation_json=fraud_engine.explanations_to_json(result.explanations),
    )
    db.add(transaction)
    db.flush()

    gateway = get_payment_gateway(get_settings().payment_provider)
    gw_result = gateway.create_intent(payload.amount, payload.currency, idempotency_key)

    intent = PaymentIntent(
        user_id=current_user.id,
        transaction_id=transaction.id,
        idempotency_key=idempotency_key,
        provider=gw_result.get("provider", get_settings().payment_provider),
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

    try:
        db.commit()
        db.refresh(intent)
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(PaymentIntent)
            .filter(PaymentIntent.user_id == current_user.id, PaymentIntent.idempotency_key == idempotency_key)
            .first()
        )
        if existing:
            write_audit_log(db, current_user, "payments.intent_replayed", "success", request, {"intent_id": existing.id})
            return PaymentIntentResponse(intent=serialize_payment_intent(existing), confidence=existing.confidence)
        raise

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


@router.post("/intents/{intent_id}/request-otp", response_model=OTPRequestResponse)
def request_step_up_otp(
    intent_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OTPRequestResponse:
    intent = (
        db.query(PaymentIntent)
        .filter(PaymentIntent.id == intent_id, PaymentIntent.user_id == current_user.id)
        .first()
    )
    if intent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment intent not found")
    if intent.status != "requires_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only payments under review are eligible for step-up verification",
        )

    # Generate 6-digit numeric OTP
    otp_code = f"{secrets.randbelow(900000) + 100000}"
    intent.otp_code_hash = pwd_context.hash(otp_code)
    intent.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.commit()

    write_audit_log(
        db,
        current_user,
        "payments.otp_requested",
        "success",
        request,
        {"intent_id": intent.id, "expires_at": intent.otp_expires_at.isoformat()},
    )

    return OTPRequestResponse(
        message="Verification OTP generated. Complete 2FA challenge to authorize transaction.",
        demo_otp=otp_code,
        expires_in_seconds=600,
    )


@router.post("/intents/{intent_id}/verify-otp", response_model=PaymentIntentRead)
def verify_step_up_otp(
    intent_id: int,
    payload: OTPVerifyRequest,
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
    if intent.status != "requires_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only payments under review can be verified via OTP",
        )
    if not intent.otp_code_hash or not intent.otp_expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active OTP challenge found. Please request a verification OTP first.",
        )
    otp_expires = intent.otp_expires_at
    if otp_expires.tzinfo is None:
        otp_expires = otp_expires.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > otp_expires:
        intent.otp_code_hash = None
        intent.otp_expires_at = None
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification code has expired.")

    if not pwd_context.verify(payload.otp.strip(), intent.otp_code_hash):
        write_audit_log(
            db,
            current_user,
            "payments.otp_verify",
            "failure",
            request,
            {"intent_id": intent.id},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code.")

    intent.status = "approved_step_up"
    intent.provider_reference = f"stepup_{uuid4().hex[:16]}"
    intent.otp_code_hash = None
    intent.otp_expires_at = None
    db.commit()
    db.refresh(intent)

    write_audit_log(
        db,
        current_user,
        "payments.otp_verify",
        "success",
        request,
        {"intent_id": intent.id, "provider_reference": intent.provider_reference},
    )
    return serialize_payment_intent(intent)


@router.post("/webhook")
async def handle_payment_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    settings = get_settings()
    secret = settings.webhook_secret or "default-dev-webhook-secret"

    signature_header = request.headers.get("X-Signature")
    timestamp_header = request.headers.get("X-Timestamp")

    if not signature_header or not timestamp_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required X-Signature or X-Timestamp webhook headers",
        )

    # Validate timestamp tolerance (5 minutes)
    try:
        req_timestamp = float(timestamp_header)
        now_ts = datetime.now(timezone.utc).timestamp()
        if abs(now_ts - req_timestamp) > 300:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Webhook timestamp outside allowed tolerance window",
            )
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid timestamp header format")

    raw_body = await request.body()
    # Compute HMAC-SHA256 signature
    expected_sig = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp_header}.".encode("utf-8") + raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature_header, expected_sig):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook HMAC signature")

    try:
        data = json.loads(raw_body.decode("utf-8"))
        payload = WebhookPayload(**data)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Malformed payload: {exc}")

    intent = None
    if payload.intent_id:
        intent = db.query(PaymentIntent).filter(PaymentIntent.id == payload.intent_id).first()
    elif payload.provider_reference:
        intent = db.query(PaymentIntent).filter(PaymentIntent.provider_reference == payload.provider_reference).first()

    if intent:
        if payload.event == "payment.captured":
            intent.status = "settled"
        elif payload.event == "payment.failed":
            intent.status = "failed"
        db.commit()

    write_audit_log(
        db,
        None,
        "payments.webhook_received",
        "success",
        request,
        {"event": payload.event, "matched_intent_id": intent.id if intent else None},
    )

    return {"status": "success", "event": payload.event}

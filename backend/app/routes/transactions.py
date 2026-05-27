from io import StringIO
import csv

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Transaction, User
from app.schemas import AnalyzeResponse, RiskLevel, TransactionCreate, TransactionRead
from app.security import get_current_user
from app.services.fraud_engine import fraud_engine


router = APIRouter(prefix="/transactions", tags=["transactions"])


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


@router.post("/analyze", response_model=AnalyzeResponse, status_code=status.HTTP_201_CREATED)
def analyze_transaction(
    payload: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalyzeResponse:
    result = fraud_engine.analyze(payload)
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
    db.commit()
    db.refresh(transaction)
    return AnalyzeResponse(transaction=serialize_transaction(transaction), confidence=result.confidence)


@router.get("", response_model=list[TransactionRead])
def list_transactions(
    risk_level: RiskLevel | None = None,
    search: str | None = Query(default=None, max_length=120),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TransactionRead]:
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)
    if risk_level:
        query = query.filter(Transaction.risk_level == risk_level)
    if search:
        pattern = f"%{search.strip().lower()}%"
        query = query.filter(or_(Transaction.receiver_id.like(pattern), Transaction.note.like(pattern)))

    records = query.order_by(Transaction.created_at.desc()).offset(skip).limit(limit).all()
    return [serialize_transaction(record) for record in records]


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    db.query(Transaction).filter(Transaction.user_id == current_user.id).delete(synchronize_session=False)
    db.commit()


@router.get("/export.csv")
def export_transactions_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    records = (
        db.query(Transaction)
        .filter(Transaction.user_id == current_user.id)
        .order_by(Transaction.created_at.desc())
        .all()
    )

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "created_at",
            "amount",
            "transaction_type",
            "channel",
            "receiver_id",
            "risk_score",
            "risk_level",
            "recommendation",
            "top_reason",
        ]
    )
    for record in records:
        reasons = fraud_engine.explanations_from_json(record.explanation_json)
        writer.writerow(
            [
                record.id,
                record.created_at.isoformat(),
                record.amount,
                record.transaction_type,
                record.channel,
                record.receiver_id,
                record.risk_score,
                record.risk_level,
                record.recommendation,
                reasons[0].title if reasons else "",
            ]
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=fraudshield-report.csv"},
    )


@router.get("/{transaction_id}", response_model=TransactionRead)
def get_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionRead:
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == current_user.id)
        .first()
    )
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return serialize_transaction(transaction)

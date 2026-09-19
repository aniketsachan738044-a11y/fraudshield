from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Transaction, User
from app.schemas import AnalyticsSummary, ModelMetrics, RetrainResponse, RiskBreakdownItem
from app.security import get_current_user
from app.services.fraud_engine import fraud_engine


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalyticsSummary:
    base = db.query(Transaction).filter(Transaction.user_id == current_user.id)
    total_transactions = base.count()
    total_amount = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(Transaction.user_id == current_user.id).scalar()
    average_risk_score = (
        db.query(func.coalesce(func.avg(Transaction.risk_score), 0))
        .filter(Transaction.user_id == current_user.id)
        .scalar()
    )
    high_risk_count = base.filter(Transaction.risk_level == "high").count()
    medium_risk_count = base.filter(Transaction.risk_level == "medium").count()
    low_risk_count = base.filter(Transaction.risk_level == "low").count()

    return AnalyticsSummary(
        total_transactions=total_transactions,
        total_amount=round(float(total_amount), 2),
        average_risk_score=round(float(average_risk_score), 2),
        high_risk_count=high_risk_count,
        medium_risk_count=medium_risk_count,
        low_risk_count=low_risk_count,
    )


@router.get("/risk-breakdown", response_model=list[RiskBreakdownItem])
def risk_breakdown(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RiskBreakdownItem]:
    rows = (
        db.query(Transaction.risk_level, func.count(Transaction.id))
        .filter(Transaction.user_id == current_user.id)
        .group_by(Transaction.risk_level)
        .all()
    )
    counts = {label: count for label, count in rows}
    return [
        RiskBreakdownItem(label="low", count=counts.get("low", 0)),
        RiskBreakdownItem(label="medium", count=counts.get("medium", 0)),
        RiskBreakdownItem(label="high", count=counts.get("high", 0)),
    ]


@router.get("/model-metrics", response_model=ModelMetrics)
def model_metrics(_: User = Depends(get_current_user)) -> ModelMetrics:
    return fraud_engine.evaluate_demo_model()


@router.post("/retrain", response_model=RetrainResponse)
def retrain_model(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RetrainResponse:
    feedback_records = (
        db.query(Transaction)
        .filter(Transaction.user_id == current_user.id, Transaction.is_fraud_confirmed.isnot(None))
        .all()
    )
    if not feedback_records:
        feedback_records = db.query(Transaction).filter(Transaction.user_id == current_user.id).limit(100).all()

    return fraud_engine.retrain_with_feedback(feedback_records)



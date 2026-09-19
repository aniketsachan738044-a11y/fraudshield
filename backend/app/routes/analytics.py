from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BlocklistEntry, Transaction, User
from app.schemas import (
    AnalyticsSummary,
    CaseInvestigationRequest,
    GraphEdge,
    GraphNode,
    ModelMetrics,
    NetworkGraphResponse,
    RetrainResponse,
    RiskBreakdownItem,
    SARReportResponse,
)
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


@router.get("/network-graph", response_model=NetworkGraphResponse)
def network_graph(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NetworkGraphResponse:
    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == current_user.id)
        .order_by(Transaction.created_at.desc())
        .limit(100)
        .all()
    )
    blocklist_values = {
        b.value.lower()
        for b in db.query(BlocklistEntry)
        .filter((BlocklistEntry.user_id == current_user.id) | (BlocklistEntry.user_id.is_(None)))
        .all()
    }

    sender_id = f"user_{current_user.id}"
    sender_total = sum(t.amount for t in transactions)
    sender_avg_risk = (sum(t.risk_score for t in transactions) / len(transactions)) if transactions else 0.0

    nodes: dict[str, GraphNode] = {
        sender_id: GraphNode(
            id=sender_id,
            label=current_user.email,
            type="sender",
            risk_score=round(sender_avg_risk, 1),
            tx_count=len(transactions),
            total_amount=round(sender_total, 2),
        )
    }

    edges: list[GraphEdge] = []
    receiver_stats: dict[str, dict] = {}
    high_risk_connections = 0

    for tx in transactions:
        target_id = f"rec_{tx.receiver_id.lower()}"
        if tx.risk_level == "high":
            high_risk_connections += 1

        if target_id not in receiver_stats:
            receiver_stats[target_id] = {
                "label": tx.receiver_id,
                "amounts": [],
                "scores": [],
                "is_blocked": tx.receiver_id.lower() in blocklist_values,
                "is_fraud": tx.is_fraud_confirmed is True,
                "has_mule_flag": "mule_fanout" in (tx.explanation_json or "") or tx.receiver_age_days <= 3,
            }
        receiver_stats[target_id]["amounts"].append(tx.amount)
        receiver_stats[target_id]["scores"].append(tx.risk_score)

        edges.append(
            GraphEdge(
                source=sender_id,
                target=target_id,
                amount=tx.amount,
                risk_level=tx.risk_level,
                risk_score=tx.risk_score,
                channel=tx.channel,
                created_at=tx.created_at,
            )
        )

    mule_clusters = 0
    for target_id, stats in receiver_stats.items():
        avg_score = sum(stats["scores"]) / len(stats["scores"])
        node_type = "receiver"
        if stats["is_blocked"]:
            node_type = "blocked"
        elif stats["is_fraud"] or stats["has_mule_flag"] or avg_score >= 65:
            node_type = "mule"
            mule_clusters += 1

        nodes[target_id] = GraphNode(
            id=target_id,
            label=stats["label"],
            type=node_type,
            risk_score=round(avg_score, 1),
            tx_count=len(stats["amounts"]),
            total_amount=round(sum(stats["amounts"]), 2),
        )

    return NetworkGraphResponse(
        nodes=list(nodes.values()),
        edges=edges,
        mule_clusters_detected=mule_clusters,
        high_risk_connections=high_risk_connections,
    )


@router.post("/investigate-case", response_model=SARReportResponse)
def investigate_case(
    payload: CaseInvestigationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SARReportResponse:
    tx = None
    if payload.transaction_id:
        tx = (
            db.query(Transaction)
            .filter(Transaction.id == payload.transaction_id, Transaction.user_id == current_user.id)
            .first()
        )
    if not tx:
        tx = (
            db.query(Transaction)
            .filter(Transaction.user_id == current_user.id)
            .order_by(Transaction.risk_score.desc())
            .first()
        )

    filing_id = f"SAR-IND-{uuid4().hex[:8].upper()}"
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    if not tx:
        return SARReportResponse(
            filing_id=filing_id,
            generated_at=now_str,
            subject_account=current_user.email,
            risk_score=0.0,
            summary="No transactions available on this account to audit.",
            forensic_timeline=["Account initialized. No anomalous transaction events recorded."],
            regulatory_violations=["None"],
            recommended_actions=["Maintain standard transaction monitoring."],
            formal_sar_narrative="Subject account displays no suspicious activity warranting regulatory disclosure.",
        )

    explanations = fraud_engine.explanations_from_json(tx.explanation_json)
    top_flags = [e.title for e in explanations]

    timeline = [
        f"[{tx.created_at.strftime('%Y-%m-%d %H:%M:%S')}] Payment intent initiated for INR {tx.amount:,.2f} via {tx.channel.upper()} to receiver '{tx.receiver_id}'.",
        f"[{tx.created_at.strftime('%Y-%m-%d %H:%M:%S')}] Telemetry resolved location '{tx.location_city or 'Unknown'}' with device trust score {tx.device_trust_score:.2f}.",
    ]
    for exp in explanations:
        timeline.append(f"[RISK ENGINE] Triggered rule '{exp.title}': {exp.detail}")

    violations = []
    if tx.risk_score >= 70 or "mule" in tx.explanation_json or "blocklist" in tx.explanation_json:
        violations.append("PMLA 2002 Section 12: Structuring & Unexplained High-Velocity Fund Transfer")
        violations.append("RBI Master Direction on Digital Payment Security: Unverified Beneficiary Anomaly")
    if tx.is_international or "impossible_travel" in tx.explanation_json:
        violations.append("FATF Recommendation 16: Cross-Border Kinematic & Wire Transfer Transparency")

    actions = [
        f"Place immediate temporary hold on beneficiary account '{tx.receiver_id}'.",
        "Submit Suspicious Transaction Report (STR) to Financial Intelligence Unit (FIU-IND).",
        "Request enhanced due diligence (EDD) and physical KYC verification from sending customer.",
    ]

    narrative = (
        f"SUSPICIOUS ACTIVITY REPORT ({filing_id})\n"
        f"SUBJECT: {current_user.email} (Account ID: {current_user.id})\n"
        f"COUNTERPARTY: {tx.receiver_id}\n"
        f"AMOUNT: INR {tx.amount:,.2f} | RISK SCORE: {tx.risk_score}/100 ({tx.risk_level.upper()})\n\n"
        f"NARRATIVE SUMMARY:\n"
        f"On {tx.created_at.strftime('%Y-%m-%d')}, our automated real-time transaction monitoring engine intercepted an anomalous "
        f"payment intent for INR {tx.amount:,.2f} routed via channel '{tx.channel}'. Forensic heuristic and machine learning scoring "
        f"flagged this transaction with a composite risk index of {tx.risk_score}/100 based on the following indicators: "
        f"{', '.join(top_flags) if top_flags else 'General anomalous variance'}.\n\n"
        f"Geographic and velocity analysis indicated non-standard beneficiary exposure (beneficiary age {tx.receiver_age_days} days). "
        f"This filing is formally submitted in accordance with statutory reporting standards for suspicious financial conduct."
    )

    return SARReportResponse(
        filing_id=filing_id,
        generated_at=now_str,
        subject_account=current_user.email,
        risk_score=tx.risk_score,
        summary=f"Transaction #{tx.id} of INR {tx.amount:,.2f} to {tx.receiver_id} flagged with risk score {tx.risk_score}/100.",
        forensic_timeline=timeline,
        regulatory_violations=violations or ["Standard Anti-Money Laundering Rule Monitoring Threshold Exceeded"],
        recommended_actions=actions,
        formal_sar_narrative=narrative,
    )




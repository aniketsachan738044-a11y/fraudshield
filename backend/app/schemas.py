from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


TransactionType = Literal["upi", "bank_transfer", "card", "wallet", "atm"]
Channel = Literal["mobile_app", "web", "qr", "payment_link", "pos", "atm"]
RiskLevel = Literal["low", "medium", "high"]
Currency = Literal["INR"]
PaymentStatus = Literal[
    "ready_for_provider",
    "requires_review",
    "blocked",
    "approved_sandbox",
    "approved_step_up",
    "settled",
    "failed",
]
PaymentDecision = Literal["allow", "review", "block"]


class OTPRequestResponse(BaseModel):
    message: str
    demo_otp: str | None = None
    expires_in_seconds: int = 600


class OTPVerifyRequest(BaseModel):
    otp: str = Field(min_length=4, max_length=10)


class WebhookPayload(BaseModel):
    event: str
    intent_id: int | None = None
    provider_reference: str | None = None
    status: str | None = None
    reason: str | None = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str | None = Field(default=None, max_length=120)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class FraudReason(BaseModel):
    code: str
    title: str
    detail: str
    severity: RiskLevel


class UserTransactionContext(BaseModel):
    tx_count_last_hour: int = 0
    tx_count_last_5m: int = 0
    avg_user_amount: float | None = None
    is_new_receiver_for_user: bool = False
    mule_distinct_receivers_15m: int = 0
    is_blocked_counterparty: bool = False
    impossible_travel_speed_kmh: float | None = None
    prev_city: str | None = None
    current_city: str | None = None


class TransactionCreate(BaseModel):
    amount: float = Field(gt=0, le=1_000_000)
    transaction_type: TransactionType
    channel: Channel
    receiver_id: str = Field(min_length=3, max_length=120)
    receiver_age_days: int = Field(default=30, ge=0, le=3650)
    hour: int | None = Field(default=None, ge=0, le=23)
    device_trust_score: float = Field(default=0.75, ge=0, le=1)
    location_mismatch: bool = False
    is_international: bool = False
    simulated_city: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=255)

    @field_validator("receiver_id")
    @classmethod
    def normalize_receiver_id(cls, value: str) -> str:
        return value.strip().lower()


class TransactionRead(TransactionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hour: int
    location_city: str | None = None
    location_lat: float | None = None
    location_lon: float | None = None
    is_fraud_confirmed: bool | None = None
    feedback_note: str | None = None
    risk_score: float
    risk_level: RiskLevel
    recommendation: str
    explanations: list[FraudReason]
    created_at: datetime


class AnalyzeResponse(BaseModel):
    transaction: TransactionRead
    confidence: float


class PaymentIntentCreate(TransactionCreate):
    currency: Currency = "INR"


class PaymentIntentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_id: int
    idempotency_key: str
    provider: str
    provider_reference: str | None
    status: PaymentStatus
    amount: float
    currency: Currency
    receiver_id: str
    risk_score: float
    risk_level: RiskLevel
    confidence: float
    decision: PaymentDecision
    decision_reason: str
    created_at: datetime
    updated_at: datetime
    transaction: TransactionRead


class PaymentIntentResponse(BaseModel):
    intent: PaymentIntentRead
    confidence: float


class AnalyticsSummary(BaseModel):
    total_transactions: int
    total_amount: float
    average_risk_score: float
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int


class RiskBreakdownItem(BaseModel):
    label: str
    count: int


class ModelMetrics(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    confusion_matrix: list[list[int]]
    note: str


class BlocklistCreate(BaseModel):
    entry_type: Literal["receiver_id", "ip_address"]
    value: str = Field(min_length=2, max_length=160)
    reason: str = Field(min_length=3, max_length=255)

    @field_validator("value")
    @classmethod
    def clean_value(cls, v: str) -> str:
        return v.strip().lower()


class BlocklistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entry_type: str
    value: str
    reason: str
    created_at: datetime


class TransactionFeedbackCreate(BaseModel):
    is_fraud: bool
    note: str | None = Field(default=None, max_length=255)


class RetrainResponse(BaseModel):
    status: str
    model_type: str
    trained_samples: int
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    message: str


class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # "sender", "receiver", "mule", "blocked"
    risk_score: float
    tx_count: int
    total_amount: float


class GraphEdge(BaseModel):
    source: str
    target: str
    amount: float
    risk_level: str
    risk_score: float
    channel: str
    created_at: datetime


class NetworkGraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    mule_clusters_detected: int
    high_risk_connections: int


class CaseInvestigationRequest(BaseModel):
    transaction_id: int | None = None
    query: str | None = None


class SARReportResponse(BaseModel):
    filing_id: str
    generated_at: str
    subject_account: str
    risk_score: float
    summary: str
    forensic_timeline: list[str]
    regulatory_violations: list[str]
    recommended_actions: list[str]
    formal_sar_narrative: str


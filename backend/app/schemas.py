from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


TransactionType = Literal["upi", "bank_transfer", "card", "wallet", "atm"]
Channel = Literal["mobile_app", "web", "qr", "payment_link", "pos", "atm"]
RiskLevel = Literal["low", "medium", "high"]
Currency = Literal["INR"]
PaymentStatus = Literal["ready_for_provider", "requires_review", "blocked", "approved_sandbox"]
PaymentDecision = Literal["allow", "review", "block"]


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


class TransactionCreate(BaseModel):
    amount: float = Field(gt=0, le=1_000_000)
    transaction_type: TransactionType
    channel: Channel
    receiver_id: str = Field(min_length=3, max_length=120)
    receiver_age_days: int = Field(default=30, ge=0, le=3650)
    hour: int = Field(ge=0, le=23)
    device_trust_score: float = Field(default=0.75, ge=0, le=1)
    location_mismatch: bool = False
    is_international: bool = False
    note: str | None = Field(default=None, max_length=255)

    @field_validator("receiver_id")
    @classmethod
    def normalize_receiver_id(cls, value: str) -> str:
        return value.strip().lower()


class TransactionRead(TransactionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
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

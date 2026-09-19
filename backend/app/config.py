from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "FraudShield"
    environment: str = "development"
    secret_key: str = Field(default="change-this-before-deployment", min_length=16)
    access_token_expire_minutes: int = 120
    auth_cookie_name: str = "fraudshield_session"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    database_url: str = "sqlite:///./fraudshield.db"
    frontend_url: str = "http://localhost:5173"
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    payment_provider: str = "sandbox"
    webhook_secret: str | None = None
    trust_proxy_headers: bool = False
    model_artifact_path: str = "artifacts/fraud_model.joblib"

    # Stripe & Razorpay Gateway Credentials
    stripe_secret_key: str | None = None
    stripe_publishable_key: str | None = None
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None

    # Redis Distributed Store
    redis_url: str | None = None

    # Twilio SMS Credentials
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None

    # SMTP Email Credentials
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "noreply@fraudshield.internal"

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.environment.lower() != "production":
            return self
        if self.secret_key == "change-this-before-deployment":
            raise ValueError("SECRET_KEY must be set to a unique high-entropy value in production")
        if not self.auth_cookie_secure:
            raise ValueError("AUTH_COOKIE_SECURE must be true in production")
        return self

    @property
    def cors_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
        if self.frontend_url and self.frontend_url not in origins:
            origins.append(self.frontend_url)
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()

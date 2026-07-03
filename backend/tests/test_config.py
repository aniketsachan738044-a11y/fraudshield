import pytest

from app.config import Settings


def test_production_rejects_default_secret() -> None:
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(
            environment="production",
            secret_key="change-this-before-deployment",
            auth_cookie_secure=True,
        )


def test_production_requires_secure_cookie() -> None:
    with pytest.raises(ValueError, match="AUTH_COOKIE_SECURE"):
        Settings(
            environment="production",
            secret_key="real-production-secret-value",
            auth_cookie_secure=False,
        )

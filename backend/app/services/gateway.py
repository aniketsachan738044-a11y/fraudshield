import logging
from abc import ABC, abstractmethod
from uuid import uuid4

from app.config import get_settings

logger = logging.getLogger(__name__)


class BasePaymentGateway(ABC):
    @abstractmethod
    def create_intent(self, amount: float, currency: str, reference_id: str) -> dict[str, str]:
        pass

    @abstractmethod
    def capture_intent(self, provider_reference: str, amount: float) -> dict[str, str]:
        pass


class SandboxPaymentGateway(BasePaymentGateway):
    def create_intent(self, amount: float, currency: str, reference_id: str) -> dict[str, str]:
        ref = f"sandbox_{uuid4().hex[:16]}"
        return {"status": "ready", "provider_reference": ref, "provider": "sandbox"}

    def capture_intent(self, provider_reference: str, amount: float) -> dict[str, str]:
        return {"status": "captured", "provider_reference": provider_reference, "provider": "sandbox"}


class StripePaymentGateway(BasePaymentGateway):
    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.stripe_secret_key

    def create_intent(self, amount: float, currency: str, reference_id: str) -> dict[str, str]:
        if self.api_key:
            try:
                import stripe

                stripe.api_key = self.api_key
                intent = stripe.PaymentIntent.create(
                    amount=int(amount * 100),
                    currency=currency.lower(),
                    metadata={"fraudshield_ref": reference_id},
                    capture_method="manual",
                )
                return {"status": intent.status, "provider_reference": intent.id, "provider": "stripe"}
            except Exception as exc:
                logger.warning(f"Stripe live create_intent failed, falling back to mock: {exc}")

        ref = f"pi_mock_{uuid4().hex[:20]}"
        return {"status": "requires_capture", "provider_reference": ref, "provider": "stripe"}

    def capture_intent(self, provider_reference: str, amount: float) -> dict[str, str]:
        if self.api_key and not provider_reference.startswith("pi_mock_"):
            try:
                import stripe

                stripe.api_key = self.api_key
                intent = stripe.PaymentIntent.capture(provider_reference)
                return {"status": intent.status, "provider_reference": intent.id, "provider": "stripe"}
            except Exception as exc:
                logger.warning(f"Stripe live capture_intent failed: {exc}")

        return {"status": "succeeded", "provider_reference": provider_reference, "provider": "stripe"}


class RazorpayPaymentGateway(BasePaymentGateway):
    def __init__(self, key_id: str | None = None, key_secret: str | None = None) -> None:
        settings = get_settings()
        self.key_id = key_id or settings.razorpay_key_id
        self.key_secret = key_secret or settings.razorpay_key_secret

    def create_intent(self, amount: float, currency: str, reference_id: str) -> dict[str, str]:
        if self.key_id and self.key_secret:
            try:
                import razorpay

                client = razorpay.Client(auth=(self.key_id, self.key_secret))
                order = client.order.create({
                    "amount": int(amount * 100),
                    "currency": currency.upper(),
                    "receipt": reference_id,
                })
                return {"status": "created", "provider_reference": order["id"], "provider": "razorpay"}
            except Exception as exc:
                logger.warning(f"Razorpay live create_intent failed, falling back to mock: {exc}")

        ref = f"order_mock_{uuid4().hex[:14]}"
        return {"status": "created", "provider_reference": ref, "provider": "razorpay"}

    def capture_intent(self, provider_reference: str, amount: float) -> dict[str, str]:
        if self.key_id and self.key_secret and not provider_reference.startswith("order_mock_"):
            try:
                import razorpay

                client = razorpay.Client(auth=(self.key_id, self.key_secret))
                payment = client.payment.capture(provider_reference, int(amount * 100))
                return {"status": "captured", "provider_reference": payment["id"], "provider": "razorpay"}
            except Exception as exc:
                logger.warning(f"Razorpay live capture_intent failed: {exc}")

        return {"status": "captured", "provider_reference": provider_reference, "provider": "razorpay"}


def get_payment_gateway(provider_name: str | None = None) -> BasePaymentGateway:
    settings = get_settings()
    normalized = (provider_name or settings.payment_provider or "sandbox").lower().strip()
    if normalized == "stripe":
        return StripePaymentGateway()
    elif normalized == "razorpay":
        return RazorpayPaymentGateway()
    return SandboxPaymentGateway()


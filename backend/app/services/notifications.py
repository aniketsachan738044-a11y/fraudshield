import logging
import smtplib
from email.mime.text import MIMEText

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


def dispatch_twilio_sms(phone_number: str, otp_code: str) -> dict[str, str]:
    settings = get_settings()
    if not (settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_from_number):
        return {"status": "skipped", "reason": "Twilio credentials not configured"}

    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
    body = f"Your FraudShield Step-Up Verification Code is: {otp_code}. Valid for 10 minutes."
    try:
        response = httpx.post(
            url,
            data={"To": phone_number, "From": settings.twilio_from_number, "Body": body},
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            timeout=5.0,
        )
        if response.is_success:
            logger.info(f"[Twilio SMS] Delivered OTP to {phone_number}")
            return {"status": "delivered", "provider": "twilio"}
        logger.warning(f"[Twilio SMS Error] HTTP {response.status_code}: {response.text}")
    except Exception as exc:
        logger.warning(f"[Twilio SMS Exception] Failed to send SMS: {exc}")

    return {"status": "failed", "provider": "twilio"}


def dispatch_smtp_email(to_email: str, otp_code: str) -> dict[str, str]:
    settings = get_settings()
    if not settings.smtp_host:
        return {"status": "skipped", "reason": "SMTP host not configured"}

    subject = "FraudShield Security Alert - Step-Up Verification Code"
    content = (
        f"A transaction requiring step-up verification was initiated on your account.\n\n"
        f"Your one-time code is: {otp_code}\n\n"
        "This code expires in 10 minutes. If you did not initiate this payment, secure your account immediately."
    )
    msg = MIMEText(content)
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=5.0) as server:
            if settings.smtp_user and settings.smtp_password:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
            logger.info(f"[SMTP Email] Delivered OTP to {to_email}")
            return {"status": "delivered", "provider": "smtp"}
    except Exception as exc:
        logger.warning(f"[SMTP Email Exception] Failed to send email: {exc}")

    return {"status": "failed", "provider": "smtp"}


def dispatch_step_up_otp(recipient: str, otp_code: str, channel: str = "sms") -> dict[str, str]:
    settings = get_settings()
    # Check if recipient is email or phone
    if "@" in recipient:
        res = dispatch_smtp_email(recipient, otp_code)
        if res.get("status") == "delivered":
            return {"status": "delivered", "channel": "email", "recipient": recipient, "provider": "smtp"}

    if settings.twilio_account_sid:
        res = dispatch_twilio_sms(recipient, otp_code)
        if res.get("status") == "delivered":
            return {"status": "delivered", "channel": "sms", "recipient": recipient, "provider": "twilio"}

    # Default fallback: structured logging for local sandbox testing
    logger.info(f"[2FA Dispatch - Sandbox] Sent {channel.upper()} OTP '{otp_code}' to {recipient}")
    return {
        "status": "delivered",
        "channel": channel,
        "recipient": recipient,
        "provider": "sandbox",
    }


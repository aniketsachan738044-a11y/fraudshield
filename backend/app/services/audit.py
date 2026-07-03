import json
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog, User


def write_audit_log(
    db: Session,
    user: User | None,
    event_type: str,
    status: str,
    request: Request | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    user_agent = request.headers.get("user-agent") if request else None
    audit_log = AuditLog(
        user_id=user.id if user else None,
        event_type=event_type,
        status=status,
        ip_address=request.client.host if request and request.client else None,
        user_agent=user_agent[:255] if user_agent else None,
        details_json=json.dumps(details or {}, default=str),
    )
    db.add(audit_log)
    db.commit()
    return audit_log

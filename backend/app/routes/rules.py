from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BlocklistEntry, User
from app.schemas import BlocklistCreate, BlocklistRead
from app.security import get_current_user
from app.services.audit import write_audit_log

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("/blocklist", response_model=list[BlocklistRead])
def list_blocklist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BlocklistRead]:
    entries = (
        db.query(BlocklistEntry)
        .filter((BlocklistEntry.user_id == current_user.id) | (BlocklistEntry.user_id.is_(None)))
        .order_by(BlocklistEntry.created_at.desc())
        .all()
    )
    return [BlocklistRead.model_validate(e) for e in entries]


@router.post("/blocklist", response_model=BlocklistRead, status_code=status.HTTP_201_CREATED)
def add_blocklist_entry(
    payload: BlocklistCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BlocklistRead:
    existing = (
        db.query(BlocklistEntry)
        .filter(
            BlocklistEntry.user_id == current_user.id,
            BlocklistEntry.entry_type == payload.entry_type,
            BlocklistEntry.value == payload.value,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Entry already exists on the blocklist",
        )

    entry = BlocklistEntry(
        user_id=current_user.id,
        entry_type=payload.entry_type,
        value=payload.value,
        reason=payload.reason,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    write_audit_log(
        db,
        current_user,
        "rules.blocklist_added",
        "success",
        request,
        {"entry_id": entry.id, "type": entry.entry_type, "value": entry.value},
    )
    return BlocklistRead.model_validate(entry)


@router.delete("/blocklist/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_blocklist_entry(
    entry_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    entry = (
        db.query(BlocklistEntry)
        .filter(BlocklistEntry.id == entry_id, BlocklistEntry.user_id == current_user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blocklist entry not found")

    db.delete(entry)
    db.commit()

    write_audit_log(
        db,
        current_user,
        "rules.blocklist_deleted",
        "success",
        request,
        {"entry_id": entry_id},
    )

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.rate_limit import limit_login_attempts
from app.schemas import LoginRequest, Token, UserCreate, UserRead
from app.security import clear_auth_cookie, create_access_token, get_current_user, hash_password, set_auth_cookie, verify_password
from app.services.audit import write_audit_log


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(request: Request, response: Response, payload: UserCreate, db: Session = Depends(get_db)) -> Token:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.email)
    set_auth_cookie(response, token)
    write_audit_log(db, user, "auth.register", "success", request)
    return Token(access_token=token, user=UserRead.model_validate(user))


@router.post("/login", response_model=Token)
def login(request: Request, response: Response, payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    limit_login_attempts(request)
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        write_audit_log(db, user, "auth.login", "failure", request, {"email": str(payload.email)})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(user.email)
    set_auth_cookie(response, token)
    write_audit_log(db, user, "auth.login", "success", request)
    return Token(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    write_audit_log(db, current_user, "auth.logout", "success", request)
    clear_auth_cookie(response)

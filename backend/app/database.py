from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
is_sqlite = settings.database_url.startswith("sqlite")
engine_kwargs = {}
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    if is_sqlite:
        from sqlalchemy import text
        with engine.begin() as conn:
            res = conn.execute(text("PRAGMA table_info(transactions);")).fetchall()
            existing_cols = {row[1] for row in res}
            for col_name, col_type in [
                ("location_city", "VARCHAR(100)"),
                ("location_lat", "FLOAT"),
                ("location_lon", "FLOAT"),
                ("is_fraud_confirmed", "BOOLEAN"),
                ("feedback_note", "VARCHAR(255)"),
            ]:
                if col_name not in existing_cols and "id" in existing_cols:
                    conn.execute(text(f"ALTER TABLE transactions ADD COLUMN {col_name} {col_type};"))

    # Ensure default demo user exists for fresh cloud deployments
    with SessionLocal() as db:
        existing_user = db.query(models.User).filter(models.User.email == "test@example.com").first()
        if not existing_user:
            from app.security import hash_password
            demo = models.User(
                email="test@example.com",
                full_name="aniket",
                hashed_password=hash_password("password123"),
            )
            db.add(demo)
            db.commit()



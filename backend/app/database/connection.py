"""
Database engine + session management.

Models are created progressively in later stages (app/models/*.py). This
module only owns the engine/session lifecycle so it can be imported safely
from app.main during Stage 2 without any ORM models existing yet.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT_SECONDS,
    pool_pre_ping=True,   # avoids "server closed the connection unexpectedly" errors
    echo=settings.DB_ECHO,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency. Usage:

        @router.get("/cameras")
        def list_cameras(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context-manager form for use outside of FastAPI request handlers
    (background workers, scripts, WebSocket broadcast tasks, etc.)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_database_connection() -> tuple[bool, str | None]:
    """
    Used by the /health endpoint and startup checks.
    Returns (is_healthy, error_message).
    Never raises — callers should treat a False result as a degraded state,
    not a hard crash, since the API should still start and report status.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:  # noqa: BLE001 - we want to report *any* DB failure
        logger.error("Database connectivity check failed", extra={"error": str(exc)})
        return False, str(exc)


def create_all_tables() -> None:
    """
    Create all tables registered on Base.metadata.
    Intended for local/dev bootstrapping only — production environments
    should use Alembic migrations (see scripts/ and alembic/ once added).
    """
    from app.database.base import Base  # local import avoids circulars

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created (Base.metadata.create_all)")

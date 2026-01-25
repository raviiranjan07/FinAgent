"""Database connection management for FinAgent."""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from database.models import Base

# Database URL from environment or default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://finagent:finagent_secret@localhost:5432/finagent"
)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
    echo=os.getenv("SQL_DEBUG", "false").lower() == "true"
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables.

    Note: For production, use Alembic migrations instead.
    This is for development convenience.
    """
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session as a generator (for dependency injection).

    Usage:
        db = next(get_db())
        try:
            # use db
        finally:
            db.close()

    Or with FastAPI:
        @app.get("/")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get database session as a context manager.

    Usage:
        with get_db_session() as db:
            # use db
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_connection():
    """Get raw psycopg2 database connection for migrations.

    Returns a raw connection object (not SQLAlchemy session).
    Used by migration scripts that need cursor access.

    Returns:
        psycopg2 connection object
    """
    return engine.raw_connection()


def check_db_connection() -> bool:
    """Check if database connection is working."""
    try:
        with get_db_session() as db:
            db.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

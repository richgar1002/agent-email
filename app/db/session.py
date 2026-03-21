"""Database session and connection management"""
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

# Use SQLite for local dev, Postgres for production
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agent_email.db")

# Convert to PostgreSQL format if using Postgres
if "postgres" in DATABASE_URL and "postgresql+" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

# SQLite doesn't support pool_pre_ping
if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Get database session as context manager"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    from app.db.models import Organization, Agent, Mailbox, ApiToken, Message, Thread, Draft, Webhook, AuditLog
    Base.metadata.create_all(bind=engine)
